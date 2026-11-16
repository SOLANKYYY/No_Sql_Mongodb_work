# Implementation notes

## Bank transfer (Lab 10.1)

`accounts` documents contain `account_id`, `balance` and `version`. Balances are
integer paise to avoid binary floating-point money calculations. `account_id`
and `transaction_history.transfer_id` have unique indexes. The transaction
reads the account, conditionally debits using sufficient balance plus the read
version, credits the destination, and inserts history in the same session.
A missing source/destination or insufficient funds raises a business exception.
Every update's match count is checked. Version increments use one `$inc` document.

The lab compares a successful transfer, insufficient funds, an intentional
exception after a debit, a real stale-snapshot conflict, and reusing an already
committed transfer ID. Failed cases compare complete account records and the
history count. The sum of both account balances must remain 150000 paise.
The conflict test deliberately advances an account version outside the first
transaction's snapshot to create a genuine server conflict; it is labeled as
controlled contention, not a naturally observed production event.

## Retry semantics

`transaction()` uses `start_session()` and `start_transaction()` with
`ReadConcern('snapshot')` and `WriteConcern(w='majority', j=True)`.
A `TransientTransactionError` aborts the current attempt and retries the whole
body, with 0.1 * 2**attempt seconds of backoff. Five retries allow six total
attempts. Insufficient funds, no stock and other application errors abort once.
An `UnknownTransactionCommitResult` retries the commit of that same transaction.
If commit remains uncertain after bounded attempts, the caller receives an
explicit unknown-outcome error and must inspect the operation ID before retrying.

A thread-safe MongoClient is shared by workers; each operation creates its own
session. The default pool supports the lab's maximum 16 threads. Local connection
and operation timeouts bound waits when the lab is unavailable. No connection
strings or credentials are packaged.

## Inventory (Lab 10.2)

`inventory`: product_id, name, stock, version.
`orders`: order_id, customer_id, items[{product_id, qty, price}], status, total.
Unique indexes enforce product and order identities. A guarded decrement and
pending order insertion share a transaction. The version predicate is checked
alongside sufficient stock. The example product price is a fixed 10.00, and
quantities must be positive integers.

Eight threads first read five available units behind a barrier. This controlled
schedule makes conflicting snapshots observable. Separate fresh products are
used for retry limits zero and five. All per-request outcomes and retries are
recorded. Exactly five successful reservations and three business rejections
are the target, not hardcoded output. The script additionally checks:

- stock is nonnegative;
- remaining stock + created orders equals starting stock;
- created orders equals acknowledged reservations.

The nontransactional comparison uses an atomic `find_one_and_update` stock guard,
which avoids negative stock, followed by a separate order insert. An intentional
exception between the two shows the cross-document inconsistency. The same
exception inside a transaction must leave stock/version/orders unchanged.

## Throughput

Each mode runs 64 requests against 64 units at 1, 4, 8 and 16 threads, three times.
The mode order alternates across repeats. Both modes use majority+j:true; the
nontransactional path pays for two separate acknowledged writes. Timing includes
executor startup, writes, retries, and rejected requests. Throughput counts only
successful reservations, so errors cannot inflate it. The chart plots median
throughput and min/max range. There is no artificial barrier or delay in timed
trials and no guaranteed rising curve. Results are a local teaching experiment,
not a statistically comprehensive performance study.

## Durability

A transaction commits a ledger and audit document with majority+j:true. Their
marker and the three server process IDs are saved. The orchestrator sends
SIGKILL to only this lab's three containers, restarts them with the same volumes,
and waits for the replica set. Each member must have a different process ID and
contain both complete documents. This verifies a real process restart rather
than merely re-reading data without restarting. It is not a physical power-loss,
filesystem-corruption or hardware durability test.

## Result provenance

Every result includes run ID, timestamps, MongoDB version, topology, database
name, measurements and verification flags. A unique database name per activity
and run avoids deleting previous experiments. File writes use an atomic temporary
file replacement. PDF evidence hashes identify the JSON used to generate it.
The source package has no precomputed passing results. Synthetic data used for
layout testing stays outside the delivered package.

## Review and execution limits

18 Python unit tests passed during preparation. These use mock clients for
control-flow checks, including six bounded unknown-commit attempts and no body
replay on an uncertain commit. Python syntax, shell syntax and package integrity
are checked separately. Actual Docker operations, PowerShell invocation and
MongoDB state checks require a run on the student's machine; they are not claimed
as executed in the preparation environment. `run-all.ps1` is the complete live
verification path. An unsuccessful invariant produces an error and the publisher
refuses failed evidence.
