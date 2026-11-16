"""Standalone Exercise 10 CLI. All results originate from live MongoDB operations."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import threading
import time
from uuid import uuid4
from pymongo import MongoClient, ReadPreference
from pymongo.errors import PyMongoError, OperationFailure
from pymongo.write_concern import WriteConcern
from transactions import (transfer, reserve_inventory, reserve_without_transaction,
                          InsufficientFunds, OutOfStock, InjectedFailure, CommitOutcomeUnknown, utcnow)

HOSTS = os.getenv('EX10_HOSTS', 'ex10-mongo1:27017,ex10-mongo2:27017,ex10-mongo3:27017').split(',')
OUT = Path(os.getenv('RESULTS_DIR', '/results'))
MAJORITY = WriteConcern(w='majority', j=True, wtimeout=10000)


def connection(host=None):
    # One shared client supports up to 16 worker threads; default pool (100) suffices.
    # These bounds are for small local lab operations, not long production queries.
    return MongoClient(host or ('mongodb://' + ','.join(HOSTS) + '/?replicaSet=ex10'),
                       directConnection=bool(host), serverSelectionTimeoutMS=5000,
                       connectTimeoutMS=5000, socketTimeoutMS=20000,
                       appname='Exercise10Standalone')


def healthy(client, timeout=120):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            s = client.admin.command('replSetGetStatus')
            if s['set'] != 'ex10':
                raise RuntimeError('Only the isolated ex10 replica set may be used')
            if len(s['members']) == 3 and all(m['health'] == 1 for m in s['members']) and sorted(m['stateStr'] for m in s['members']) == ['PRIMARY','SECONDARY','SECONDARY']:
                return s
        except PyMongoError:
            pass
        time.sleep(1)
    raise RuntimeError('The three-member ex10 replica set is not healthy')


def states(client):
    return [{'name': m['name'], 'state': m['stateStr'], 'health': m['health']}
            for m in healthy(client)['members']]


def initialize():
    for host in HOSTS:
        with connection(host) as c:
            deadline = time.monotonic() + 90
            while True:
                try:
                    c.admin.command('ping'); break
                except PyMongoError:
                    if time.monotonic() > deadline: raise
                    time.sleep(1)
    with connection(HOSTS[0]) as c:
        try:
            c.admin.command('replSetInitiate', {'_id':'ex10', 'members':[{'_id':i,'host':h} for i,h in enumerate(HOSTS)]})
        except OperationFailure as e:
            if e.code != 23: raise
    with connection() as c:
        for m in states(c): print(f"  {m['name']:<23} {m['state']:<10} health={m['health']:g}", flush=True)
    print('Exercise 10 standalone replica set ready.', flush=True)


def save(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / name
    tmp = dest.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')
    tmp.replace(dest)
    print('Saved ' + str(dest), flush=True)


def load(name):
    return json.loads((OUT/name).read_text(encoding='utf-8'))


def envelope(client, activity):
    return {'format':'exercise10-transactions', 'version':1, 'activity':activity,
            'runId':uuid4().hex, 'startedAt':utcnow(), 'mongoVersion':client.server_info()['version'],
            'members':states(client), 'readConcern':'snapshot', 'writeConcern':{'w':'majority','j':True},
            'source':'live MongoDB lab run'}


def labdb(client, run_id, activity):
    # Unique database per run preserves earlier experiments. Never connects to Signal Desk.
    return client.get_database('ex10_lab_' + activity + '_' + run_id, write_concern=MAJORITY)


def account_state(db):
    return {'accounts':list(db.accounts.find({}, {'_id':0}).sort('account_id',1)),
            'historyCount':db.transaction_history.count_documents({})}


def bank():
    print('\nLAB 10.1 - BANK TRANSFER, ROLLBACK AND EXPONENTIAL RETRY', flush=True)
    with connection() as c:
        result = envelope(c, 'bank'); db = labdb(c, result['runId'], 'bank')
        db.accounts.create_index('account_id', unique=True)
        db.transaction_history.create_index('transfer_id', unique=True)
        db.accounts.insert_many([{'account_id':'ACC-001','balance':100000,'version':0},
                                 {'account_id':'ACC-002','balance':50000,'version':0}])
        result.update(database=db.name, currencyUnit='integer paise (100 paise = INR 1)', cases=[])

        def case(name, amount, expected, **kwargs):
            before = account_state(db); trace = []; operation_id = uuid4().hex
            tick = time.perf_counter()
            try:
                transfer(c, db, 'ACC-001','ACC-002', amount, operation_id=operation_id, trace=trace, **kwargs)
                outcome, error = 'committed', None
            except (InsufficientFunds, InjectedFailure, ValueError) as exc:
                outcome, error = 'aborted', type(exc).__name__ + ': ' + str(exc)
            after = account_state(db)
            unchanged = before == after
            passed = outcome == expected and (unchanged if expected=='aborted' else
                after['accounts'][0]['balance'] == before['accounts'][0]['balance'] - amount and
                after['accounts'][1]['balance'] == before['accounts'][1]['balance'] + amount and
                after['historyCount'] == before['historyCount'] + 1)
            row = {'name':name,'amount':amount,'operationId':operation_id,'outcome':outcome,'error':error,
                   'before':before,'after':after,'unchanged':unchanged,'verified':passed,'retries':trace,
                   'elapsedMs':round((time.perf_counter()-tick)*1000,3)}
            result['cases'].append(row)
            print(f"\n{name}: {outcome.upper()} | verified={passed}", flush=True)
            print('  Before:', before, flush=True); print('  After: ', after, flush=True)
            if error: print('  ' + error, flush=True)
            for event in trace: print('  RETRY:', event, flush=True)
            return operation_id

        success_id = case('Successful transfer',25000,'committed')
        case('Insufficient funds',200000,'aborted')
        case('Failure after debit before credit',5000,'aborted',fail_after_debit=True)
        # Force a REAL server write conflict: change version outside the transaction
        # after its first read establishes a snapshot. Only the first attempt does this.
        def competing_write(session, attempt):
            if attempt == 0:
                db.accounts.update_one({'account_id':'ACC-001'},{'$inc':{'version':1}})
        case('Real write conflict with retry',10000,'committed',after_read=competing_write)
        before = account_state(db)
        repeat = transfer(c,db,'ACC-001','ACC-002',25000,operation_id=success_id)
        result['duplicateCheck']={'alreadyCommitted':repeat['alreadyCommitted'], 'unchanged':before==account_state(db)}
        result['final'] = account_state(db)
        result['totalBalance'] = sum(a['balance'] for a in result['final']['accounts'])
        result['history'] = list(db.transaction_history.find({}, {'_id':0}))
        result['verified'] = all(r['verified'] for r in result['cases']) and result['totalBalance']==150000 and all(result['duplicateCheck'].values()) and any(e['label']=='TransientTransactionError' for e in result['cases'][-1]['retries'])
        result['finishedAt']=utcnow();save('lab_10_1_bank.json',result)
        if not result['verified']: raise RuntimeError('A bank invariant failed; inspect recorded evidence')


def product(db, product_id, stock):
    db.inventory.insert_one({'product_id':product_id,'name':'Lab headphones','stock':stock,'version':0})


def stock_state(db, product_id):
    item=db.inventory.find_one({'product_id':product_id},{'_id':0})
    return {'stock':item['stock'],'version':item['version'],
            'orders':db.orders.count_documents({'items.product_id':product_id})}


def reservations(client, db, product_id, *, workers, requests, initial_stock,
                 retries=5, mode='transaction', contention=False):
    product(db,product_id,initial_stock)
    barrier = threading.Barrier(workers) if contention else None
    def worker(i):
        trace=[]; tick=time.perf_counter()
        def synchronize(session, attempt):
            if attempt == 0 and barrier:
                barrier.wait(timeout=30)
        try:
            if mode=='transaction':
                reserve_inventory(client,db,product_id,1,f'C-{i}',max_retries=retries,trace=trace,after_read=synchronize)
            else:
                reserve_without_transaction(db,product_id,1,f'C-{i}')
            outcome='reserved';error=None
        except OutOfStock as exc: outcome='out_of_stock';error=str(exc)
        except CommitOutcomeUnknown as exc: outcome='unknown_commit';error=str(exc)
        except PyMongoError as exc:
            outcome='retry_exhausted' if retries and exc.has_error_label('TransientTransactionError') else 'database_error'
            error=type(exc).__name__+': '+str(exc)[:200]
        except Exception as exc: outcome='error';error=type(exc).__name__+': '+str(exc)[:200]
        return {'request':i,'outcome':outcome,'error':error,'retries':trace,'elapsedMs':round((time.perf_counter()-tick)*1000,3)}
    tick=time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes=list(pool.map(worker,range(requests)))
    elapsed=time.perf_counter()-tick
    final=stock_state(db,product_id)
    counts={name:sum(r['outcome']==name for r in outcomes) for name in ('reserved','out_of_stock','retry_exhausted','database_error','unknown_commit','error')}
    retries_count=sum(len([t for t in r['retries'] if t['kind']=='transaction-retry']) for r in outcomes)
    conserved=final['stock']>=0 and final['stock']+final['orders']==initial_stock and final['orders']==counts['reserved']
    row={'mode':mode,'workers':workers,'requests':requests,'initialStock':initial_stock,'maxRetries':retries,
         'contentionBarrier':contention,'counts':counts,'final':final,'elapsedSeconds':elapsed,
         'successfulPerSecond':counts['reserved']/elapsed,'transactionRetries':retries_count,
         'consistent':conserved,'outcomes':outcomes}
    print(f"  {mode:<15} threads={workers:2} success={counts['reserved']:3}/{requests} stock={final['stock']:3} orders={final['orders']:3} retries={retries_count:3} throughput={row['successfulPerSecond']:.2f}/s consistent={conserved}",flush=True)
    return row


def inventory():
    print('\nLAB 10.2 - INVENTORY RESERVATIONS AND WRITE CONFLICTS',flush=True)
    with connection() as c:
        result=envelope(c,'inventory');db=labdb(c,result['runId'],'inventory')
        db.inventory.create_index('product_id',unique=True)
        db.orders.create_index('order_id',unique=True)
        result.update(database=db.name,scarcity=[],benchmarks=[],failureComparison=[])
        print('\n8 simultaneous shoppers, 5 units; synchronized first reads create real contention.',flush=True)
        for retries in (0,5):
            result['scarcity'].append(reservations(c,db,'scarcity-'+str(retries),workers=8,requests=8,initial_stock=5,retries=retries,contention=True))
            for r in result['scarcity'][-1]['outcomes']:
                print(f"    Request {r['request']}: {r['outcome']} | retries={len(r['retries'])}",flush=True)
        print('\nOrder insertion failure after stock decrement: transaction versus no transaction',flush=True)
        for mode in ('transaction','nontransaction'):
            key='failure-'+mode;product(db,key,5);before=stock_state(db,key)
            try:
                if mode=='transaction':reserve_inventory(c,db,key,1,'failure-demo',fail_after_decrement=True)
                else:reserve_without_transaction(db,key,1,'failure-demo',fail_after_decrement=True)
                outcome='unexpected_success'
            except InjectedFailure:outcome='injected_failure'
            after=stock_state(db,key)
            row={'mode':mode,'before':before,'after':after,'outcome':outcome,'unchanged':before==after}
            result['failureComparison'].append(row);print(' ',row,flush=True)
        print('\nThroughput: 64 requests, stock 64, three repeats per mode/thread count.',flush=True)
        print('No artificial delay/barrier in throughput tests; both modes use majority+j:true.',flush=True)
        for repeat in range(3):
            for workers in (1,4,8,16):
                modes=('transaction','nontransaction') if repeat%2==0 else ('nontransaction','transaction')
                for mode in modes:
                    row=reservations(c,db,f'bench-{repeat}-{workers}-{mode}',workers=workers,requests=64,initial_stock=64,mode=mode)
                    row['repeat']=repeat+1
                    # Detailed worker evidence is retained, not replaced with an assumed curve.
                    result['benchmarks'].append(row)
        result['methodology']={'requestsPerTrial':64,'repeats':3,'workers':[1,4,8,16],
                               'throughput':'successful reservations / wall seconds, including retries and executor startup',
                               'plot':'median of three trials, min/max range',
                               'comparison':'same majority+j:true durability; nontransaction uses find_one_and_update then separate order insert',
                               'warning':'A throughput increase or plateau is not guaranteed. Record observed results.'}
        result['verified']=all(r['consistent'] for r in result['scarcity']+result['benchmarks']) and result['failureComparison'][0]['unchanged'] and result['failureComparison'][1]['after']=={'stock':4,'version':1,'orders':0}
        result['expectedFiveReserved']=result['scarcity'][1]['counts']['reserved']==5 and result['scarcity'][1]['counts']['out_of_stock']==3
        result['finishedAt']=utcnow();save('lab_10_2_inventory.json',result)
        print('With retries: five reserved / three out of stock observed:',result['expectedFiveReserved'],flush=True)
        if not result['verified']:raise RuntimeError('An inventory invariant failed; inspect evidence')


def process_ids():
    result = {}
    for host in HOSTS:
        with connection(host) as c:
            result[host] = str(c.admin.command('hello')['topologyVersion']['processId'])
    return result


def durability_prepare():
    with connection() as c:
        result=envelope(c,'durability');db=labdb(c,result['runId'],'durability')
        db.ledger.create_index('marker',unique=True);db.audit.create_index('marker',unique=True)
        marker=uuid4().hex
        from transactions import transaction
        def body(s,attempt):
            db.ledger.insert_one({'marker':marker,'amount':12345},session=s)
            db.audit.insert_one({'marker':marker,'action':'durable-commit'},session=s)
        transaction(c,body)
        result.update(database=db.name,marker=marker,preparedAt=utcnow(),beforeProcessIds=process_ids(),
                      restartMethod='SIGKILL all three isolated lab containers; restart with original volumes',
                      limitation='Unclean process/container restart, not a power-loss or storage-corruption test')
        save('durability-pending.json',result)
        print('Committed both documents with majority + j:true. Restart nodes before verify.',flush=True)


def durability_verify():
    result=load('durability-pending.json')
    if not result['database'].startswith('ex10_lab_durability_'):raise ValueError('Unexpected evidence database')
    with connection() as c:
        result['afterMembers']=states(c)
    result['afterProcessIds']=process_ids()
    result['allProcessesRestarted']=all(result['beforeProcessIds'].get(h)!=result['afterProcessIds'].get(h) for h in HOSTS)
    observations=[]
    for host in HOSTS:
        with connection(host) as c:
            db=c.get_database(result['database'],read_preference=ReadPreference.SECONDARY_PREFERRED)
            deadline=time.monotonic()+30
            while True:
                ledger=db.ledger.find_one({'marker':result['marker']},{'_id':0})
                audit=db.audit.find_one({'marker':result['marker']},{'_id':0})
                ok=ledger=={'marker':result['marker'],'amount':12345} and audit=={'marker':result['marker'],'action':'durable-commit'}
                if ok or time.monotonic()>deadline:break
                time.sleep(.2)
            observations.append({'host':host,'ledger':ledger,'audit':audit,'present':ok})
            print(host,'both committed documents survived:',ok,flush=True)
    result.update(observations=observations,verified=result['allProcessesRestarted'] and all(r['present'] for r in observations),finishedAt=utcnow())
    save('lab_10_3_durability.json',result)
    if not result['verified']:raise RuntimeError('Durability verification failed: both documents must survive and all three process IDs must change')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['init','bank','inventory','durability-prepare','durability-verify','report','show'])
    p.add_argument('--hub-url',default=None)
    args=p.parse_args()
    if args.action=='init':initialize()
    elif args.action=='bank':bank()
    elif args.action=='inventory':inventory()
    elif args.action=='durability-prepare':durability_prepare()
    elif args.action=='durability-verify':durability_verify()
    elif args.action=='report':
        from report import generate
        generate(OUT,args.hub_url)
    elif args.action=='show':
        for name in ('lab_10_1_bank.json','lab_10_2_inventory.json','lab_10_3_durability.json'):
            r=load(name);print(name,'recorded:',r['startedAt'],'verified:',r['verified'])
        print((OUT/'faculty-results.txt').read_text() if (OUT/'faculty-results.txt').exists() else 'Run report for the formatted transcript.')


if __name__=='__main__':main()
