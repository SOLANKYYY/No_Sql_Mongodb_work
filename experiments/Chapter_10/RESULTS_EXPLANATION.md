# Explanation of measured Exercise 10 results

## Bank transfer and retry logic

The submitted bank evidence records successful debit/credit/history changes, rejection of insufficient funds, rollback after an injected post-debit failure, and a controlled real write conflict. Failed business operations leave account balances and transaction history unchanged. Total balance remains 150000 paise. A repeated committed transfer ID does not repeat the debit.

TransientTransactionError causes the entire transaction to restart with exponential backoff. UnknownTransactionCommitResult retries only commit, avoiding blind replay of a possibly committed transfer. Insufficient funds and out-of-stock are business outcomes rather than retryable write conflicts.

## Inventory contention and atomicity

Eight shoppers requested one unit each from a product with five units. With retries, five reservations succeeded and three returned out_of_stock. Final stock was 0, version 5 and order count 5; the inventory/order invariant passed. Retries show that concurrent requests encountered contention before reaching a final outcome.

When order creation was deliberately failed after the stock update, the transaction restored stock=5, version=0 and orders=0. The nontransactional comparison left stock=4, version=1 and orders=0. An atomic single-document decrement alone does not make a subsequent order insertion atomic with it.

## Throughput observations

Each configuration used 64 requests in each of three trials. All configurations completed 192 successful reservations across the three trials.

| Threads | Transaction median /s | Nontransaction median /s | Transaction retries (3 trials) |
| --- | ---: | ---: | ---: |
| 1 | 160.17 | 101.61 | 0 |
| 4 | 138.97 | 198.11 | 24 |
| 8 | 40.53 | 310.91 | 63 |
| 16 | 40.00 | 531.52 | 126 |

In this measured run, transaction throughput decreased as contention and retries increased. The nontransactional path scaled better with multiple workers, but the failure test showed its cross-document inconsistency risk. The transactional path was faster at one thread in this run; the data do not support claiming that nontransactional execution is always faster. The two modes also have different acknowledgement patterns: one transaction commit versus separately acknowledged stock and order writes. Hardware, scheduling, journaling and the limited three-trial sample affect the measurements. The chart includes trial ranges.

## Durability and journaling

The recorded durability run began at 2026-10-14T14:59:04.115435+00:00. A transaction committed both documents with majority write concern and j:true. After SIGKILL of all three dedicated MongoDB containers and restart with the same volumes, every process ID changed and both complete documents were found on all three members. This supports survival of the tested unclean process restart. It does not establish behavior under physical power loss or storage corruption.

## Publication

The first Docker push failed with HTTP 502. The later retry completed and returned the image digest recorded in DOCKER_HUB.txt. The package includes the evidence and source retrieved from that exact published image.
