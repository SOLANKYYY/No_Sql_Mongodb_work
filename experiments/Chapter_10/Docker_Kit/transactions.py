"""Exercise 10 transaction core. Real operations; explicit bounded retry logic."""
import time
from datetime import datetime, timezone
from uuid import uuid4
from pymongo import ReturnDocument, ReadPreference
from pymongo.errors import PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern


class InsufficientFunds(ValueError):
    pass


class OutOfStock(ValueError):
    pass


class InjectedFailure(RuntimeError):
    """Deliberate application exception to verify a real database rollback."""


class CommitOutcomeUnknown(RuntimeError):
    """Never report this as an abort, and never blindly replay the transaction."""


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def positive_integer(value, name):
    if type(value) is not int or value <= 0:
        raise ValueError(name + ' must be a positive integer')


def abort_if_active(session):
    if session.in_transaction:
        try:
            session.abort_transaction()
        except PyMongoError:
            # Preserve the triggering exception; server also expires aborted work.
            pass


def transaction(client, callback, *, max_retries=5, trace=None, sleep=time.sleep):
    """Retry the body only for TransientTransactionError, commit only for unknown.

    max_retries=5 permits the initial attempt plus five retries. Domain failures
    (no funds, no stock) are not transient and are never retried. Each worker gets
    its own session, while all workers share the thread-safe MongoClient.
    """
    trace = trace if trace is not None else []
    with client.start_session() as session:
        for attempt in range(max_retries + 1):
            session.start_transaction(read_concern=ReadConcern('snapshot'),
                                      write_concern=WriteConcern(w='majority', j=True, wtimeout=10000),
                                      read_preference=ReadPreference.PRIMARY,
                                      max_commit_time_ms=10000)
            try:
                value = callback(session, attempt)
                for commit_attempt in range(6):
                    try:
                        session.commit_transaction()
                        return value
                    except PyMongoError as exc:
                        if not exc.has_error_label('UnknownTransactionCommitResult'):
                            raise
                        if commit_attempt == 5:
                            raise CommitOutcomeUnknown('Commit remained uncertain; inspect operation ID before any retry.') from exc
                        delay = 0.1 * 2 ** commit_attempt
                        trace.append({'kind': 'commit-retry', 'attempt': commit_attempt + 1,
                                      'delaySeconds': delay, 'label': 'UnknownTransactionCommitResult'})
                        sleep(delay)
            except CommitOutcomeUnknown:
                # Do not abort or retry a transaction that may already be committed.
                raise
            except PyMongoError as exc:
                abort_if_active(session)
                if not exc.has_error_label('TransientTransactionError') or attempt == max_retries:
                    raise
                delay = 0.1 * 2 ** attempt
                trace.append({'kind': 'transaction-retry', 'attempt': attempt + 1,
                              'delaySeconds': delay, 'code': getattr(exc, 'code', None),
                              'label': 'TransientTransactionError'})
                sleep(delay)
            except Exception:
                abort_if_active(session)
                raise


def transfer(client, db, source, destination, amount, *, operation_id=None,
             max_retries=5, trace=None, after_read=None, fail_after_debit=False):
    positive_integer(amount, 'amount in minor currency units')
    if source == destination:
        raise ValueError('Use two different accounts')
    operation_id = operation_id or uuid4().hex

    def body(session, attempt):
        prior = db.transaction_history.find_one({'transfer_id': operation_id}, session=session)
        if prior:
            if (prior['from'], prior['to'], prior['amount']) != (source, destination, amount):
                raise ValueError('Operation ID already belongs to a different transfer')
            return {'transferId': operation_id, 'alreadyCommitted': True}
        account = db.accounts.find_one({'account_id': source}, session=session)
        if not account or account['balance'] < amount:
            raise InsufficientFunds('Source account missing or insufficient funds')
        if after_read:
            after_read(session, attempt)
        debit = db.accounts.update_one(
            {'account_id': source, 'balance': {'$gte': amount}, 'version': account['version']},
            {'$inc': {'balance': -amount, 'version': 1}}, session=session)
        if debit.matched_count != 1:
            raise InsufficientFunds('Conditional debit did not match')
        if fail_after_debit:
            raise InjectedFailure('Intentional failure after debit and before credit')
        credit = db.accounts.update_one({'account_id': destination},
                                       {'$inc': {'balance': amount, 'version': 1}}, session=session)
        if credit.matched_count != 1:
            raise ValueError('Destination account does not exist')
        db.transaction_history.insert_one({'transfer_id': operation_id, 'from': source,
                                           'to': destination, 'amount': amount, 'timestamp': utcnow()}, session=session)
        return {'transferId': operation_id, 'alreadyCommitted': False}

    return transaction(client, body, max_retries=max_retries, trace=trace)


def reserve_inventory(client, db, product_id, qty, customer_id, *, order_id=None,
                      max_retries=5, trace=None, after_read=None, fail_after_decrement=False):
    positive_integer(qty, 'quantity')
    order_id = order_id or uuid4().hex

    def body(session, attempt):
        prior = db.orders.find_one({'order_id': order_id}, session=session)
        if prior:
            if prior['customer_id'] != customer_id or prior['items'][0]['product_id'] != product_id or prior['items'][0]['qty'] != qty:
                raise ValueError('Order ID already belongs to another reservation')
            return {'orderId': order_id, 'alreadyCommitted': True}
        item = db.inventory.find_one({'product_id': product_id}, session=session)
        if not item or item['stock'] < qty:
            raise OutOfStock('Insufficient stock')
        if after_read:
            after_read(session, attempt)
        changed = db.inventory.update_one(
            {'product_id': product_id, 'stock': {'$gte': qty}, 'version': item['version']},
            {'$inc': {'stock': -qty, 'version': 1}}, session=session)
        if changed.matched_count != 1:
            raise RuntimeError('Conditional inventory update did not match')
        if fail_after_decrement:
            raise InjectedFailure('Intentional order creation failure after stock decrement')
        db.orders.insert_one({'order_id': order_id, 'customer_id': customer_id,
                              'items': [{'product_id': product_id, 'qty': qty, 'price': 10.0}],
                              'status': 'pending', 'total': round(10.0 * qty, 2)}, session=session)
        return {'orderId': order_id, 'alreadyCommitted': False}

    return transaction(client, body, max_retries=max_retries, trace=trace)


def reserve_without_transaction(db, product_id, qty, customer_id, *, order_id=None,
                                fail_after_decrement=False):
    """Atomic stock guard, but stock+order have NO combined atomicity."""
    positive_integer(qty, 'quantity')
    order_id = order_id or uuid4().hex
    item = db.inventory.find_one_and_update({'product_id': product_id, 'stock': {'$gte': qty}},
                                          {'$inc': {'stock': -qty, 'version': 1}},
                                          return_document=ReturnDocument.AFTER)
    if not item:
        raise OutOfStock('Insufficient stock')
    if fail_after_decrement:
        raise InjectedFailure('Intentional order creation failure after stock decrement')
    db.orders.insert_one({'order_id': order_id, 'customer_id': customer_id,
                          'items': [{'product_id': product_id, 'qty': qty, 'price': 10.0}],
                          'status': 'pending', 'total': round(10.0 * qty, 2)})
    return {'orderId': order_id}
