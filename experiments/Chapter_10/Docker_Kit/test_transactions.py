"""Unit tests for transaction control flow. No MongoDB or mocked performance data."""
import unittest
from unittest.mock import MagicMock, Mock
from pymongo.errors import OperationFailure
from transactions import (transaction, transfer, reserve_inventory, reserve_without_transaction,
                          InsufficientFunds, OutOfStock, InjectedFailure, CommitOutcomeUnknown)


def mongo_error(label):
    return OperationFailure('test-labelled error',112,{'code':112,'errorLabels':[label]})


def setup_client():
    client=MagicMock();session=MagicMock()
    client.start_session.return_value.__enter__.return_value=session
    session.in_transaction=True
    return client,session


class RetryTests(unittest.TestCase):
    def test_transient_replays_body_with_exponential_delays(self):
        client,s=setup_client();sleep=Mock();trace=[]
        body=Mock(side_effect=[mongo_error('TransientTransactionError'),mongo_error('TransientTransactionError'),'ok'])
        self.assertEqual(transaction(client,body,trace=trace,sleep=sleep),'ok')
        self.assertEqual(body.call_count,3)
        self.assertEqual([x.args[0] for x in sleep.call_args_list],[.1,.2])
        self.assertEqual(s.abort_transaction.call_count,2)
        s.commit_transaction.assert_called_once()

    def test_unknown_commit_retries_commit_not_body(self):
        client,s=setup_client();body=Mock(return_value='ok');sleep=Mock()
        s.commit_transaction.side_effect=[mongo_error('UnknownTransactionCommitResult'),None]
        self.assertEqual(transaction(client,body,sleep=sleep),'ok')
        body.assert_called_once();self.assertEqual(s.commit_transaction.call_count,2)
        s.abort_transaction.assert_not_called()

    def test_unknown_commit_exhaustion_is_not_reported_aborted(self):
        client,s=setup_client();body=Mock(return_value='ok')
        s.commit_transaction.side_effect=mongo_error('UnknownTransactionCommitResult')
        with self.assertRaises(CommitOutcomeUnknown):transaction(client,body,sleep=Mock())
        body.assert_called_once();s.abort_transaction.assert_not_called()
        self.assertEqual(s.commit_transaction.call_count,6)

    def test_business_rejection_aborts_without_retry(self):
        client,s=setup_client();sleep=Mock();body=Mock(side_effect=OutOfStock('empty'))
        with self.assertRaises(OutOfStock):transaction(client,body,sleep=sleep)
        body.assert_called_once();s.abort_transaction.assert_called_once();sleep.assert_not_called()
        s.commit_transaction.assert_not_called()

    def test_unlabelled_database_failure_not_retried(self):
        client,s=setup_client();body=Mock(side_effect=OperationFailure('bad query',2))
        with self.assertRaises(OperationFailure):transaction(client,body,sleep=Mock())
        body.assert_called_once()

    def test_retry_limit_is_initial_plus_five(self):
        client,s=setup_client();body=Mock(side_effect=mongo_error('TransientTransactionError'));sleep=Mock()
        with self.assertRaises(OperationFailure):transaction(client,body,sleep=sleep)
        self.assertEqual(body.call_count,6)
        self.assertEqual([x.args[0] for x in sleep.call_args_list],[.1,.2,.4,.8,1.6])

    def test_no_retry_mode(self):
        client,s=setup_client();body=Mock(side_effect=mongo_error('TransientTransactionError'))
        with self.assertRaises(OperationFailure):transaction(client,body,max_retries=0,sleep=Mock())
        body.assert_called_once()

    def test_transaction_concerns(self):
        client,s=setup_client();transaction(client,lambda session,attempt:None)
        settings=s.start_transaction.call_args.kwargs
        self.assertEqual(settings['read_concern'].level,'snapshot')
        self.assertEqual(settings['write_concern'].document['w'],'majority')
        self.assertIs(settings['write_concern'].document['j'],True)


class BusinessTests(unittest.TestCase):
    def bank(self):
        c,s=setup_client();db=MagicMock();db.transaction_history.find_one.return_value=None
        db.accounts.find_one.return_value={'balance':1000,'version':2}
        db.accounts.update_one.return_value.matched_count=1
        return c,s,db

    def test_all_transfer_writes_use_same_session(self):
        c,s,db=self.bank();transfer(c,db,'A','B',100)
        for call in db.accounts.update_one.call_args_list:self.assertIs(call.kwargs['session'],s)
        self.assertIs(db.transaction_history.insert_one.call_args.kwargs['session'],s)
        self.assertEqual(db.accounts.update_one.call_args_list[0].args[0],{'account_id':'A','balance':{'$gte':100},'version':2})

    def test_conditional_debit_zero_aborts(self):
        c,s,db=self.bank();db.accounts.update_one.return_value.matched_count=0
        with self.assertRaises(InsufficientFunds):transfer(c,db,'A','B',100)
        self.assertEqual(db.accounts.update_one.call_count,1)
        db.transaction_history.insert_one.assert_not_called();s.abort_transaction.assert_called_once()

    def test_missing_destination_aborts_after_debit(self):
        c,s,db=self.bank()
        db.accounts.update_one.side_effect=[Mock(matched_count=1),Mock(matched_count=0)]
        with self.assertRaises(ValueError):transfer(c,db,'A','B',100)
        db.transaction_history.insert_one.assert_not_called();s.abort_transaction.assert_called_once()

    def test_failure_after_debit_does_not_credit_or_commit(self):
        c,s,db=self.bank()
        with self.assertRaises(InjectedFailure):transfer(c,db,'A','B',100,fail_after_debit=True)
        self.assertEqual(db.accounts.update_one.call_count,1);s.commit_transaction.assert_not_called()
        s.abort_transaction.assert_called_once()

    def test_duplicate_transfer_no_repeated_updates(self):
        c,s,db=self.bank();db.transaction_history.find_one.return_value={'from':'A','to':'B','amount':100}
        self.assertTrue(transfer(c,db,'A','B',100,operation_id='stable')['alreadyCommitted'])
        db.accounts.update_one.assert_not_called()

    def test_duplicate_transfer_different_operation_rejected(self):
        c,s,db=self.bank();db.transaction_history.find_one.return_value={'from':'A','to':'B','amount':100}
        with self.assertRaises(ValueError):transfer(c,db,'A','B',200,operation_id='stable')
        db.accounts.update_one.assert_not_called()

    def test_invalid_amounts_rejected_before_session(self):
        for amount in (0,-1,True,1.5):
            c,s,db=self.bank()
            with self.assertRaises(ValueError):transfer(c,db,'A','B',amount)
            c.start_session.assert_not_called()

    def test_inventory_stock_guard_version_and_session(self):
        c,s=setup_client();db=MagicMock();db.orders.find_one.return_value=None
        db.inventory.find_one.return_value={'stock':5,'version':0};db.inventory.update_one.return_value.matched_count=1
        reserve_inventory(c,db,'P',1,'C')
        call=db.inventory.update_one.call_args
        self.assertEqual(call.args[0],{'product_id':'P','stock':{'$gte':1},'version':0})
        self.assertEqual(call.args[1],{'$inc':{'stock':-1,'version':1}})
        self.assertIs(call.kwargs['session'],s);self.assertIs(db.orders.insert_one.call_args.kwargs['session'],s)

    def test_out_of_stock_no_update_no_retry(self):
        c,s=setup_client();db=MagicMock();db.orders.find_one.return_value=None
        db.inventory.find_one.return_value={'stock':0,'version':5}
        with self.assertRaises(OutOfStock):reserve_inventory(c,db,'P',1,'C')
        db.inventory.update_one.assert_not_called();db.orders.insert_one.assert_not_called()
        self.assertEqual(s.start_transaction.call_count,1)

    def test_atomic_update_nontransaction_failure_stops_before_order(self):
        db=MagicMock();db.inventory.find_one_and_update.return_value={'stock':4}
        with self.assertRaises(InjectedFailure):reserve_without_transaction(db,'P',1,'C',fail_after_decrement=True)
        db.inventory.find_one_and_update.assert_called_once();db.orders.insert_one.assert_not_called()


if __name__=='__main__':unittest.main(verbosity=2)
