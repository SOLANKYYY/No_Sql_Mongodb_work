"""Exercise 13 CLI. Real observations only; no synthetic success evidence."""
import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import shutil
import sys
import threading
import time
from urllib.request import urlopen


def utc():
    return datetime.now(timezone.utc).isoformat()


def save(name, value):
    root = Path(os.getenv('RESULTS_DIR', '/results'))
    root.mkdir(parents=True, exist_ok=True)
    dest = root / name
    dest.write_text(json.dumps(value, indent=2, default=str), encoding='utf-8')
    print(json.dumps(value, indent=2, default=str))


def prepare(destination):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    secret_dir = root / '.secrets'
    secret_dir.mkdir(exist_ok=True)
    env = root / '.env'
    key = secret_dir / 'keyfile'
    if env.exists() != key.exists():
        raise RuntimeError('Incomplete credentials: retain BOTH original .env and .secrets/keyfile. Do not rotate one alone.')
    if not env.exists():
        values = {'MONGO_ADMIN_USER': 'labadmin', 'MONGO_ADMIN_PASSWORD': secrets.token_hex(24),
                  'MONGO_APP_PASSWORD': secrets.token_hex(24), 'MONGO_MONITOR_PASSWORD': secrets.token_hex(24)}
        env.write_text(''.join(f'{k}={v}\n' for k, v in values.items()), encoding='utf-8')
        key.write_text(base64.b64encode(secrets.token_bytes(756)).decode()+'\n', encoding='ascii')
    values = dict(line.split('=', 1) for line in env.read_text(encoding='utf-8-sig').splitlines() if '=' in line and not line.startswith('#'))
    for k in ['MONGO_ADMIN_USER','MONGO_ADMIN_PASSWORD','MONGO_APP_PASSWORD','MONGO_MONITOR_PASSWORD']:
        if not values.get(k): raise RuntimeError('Required credential missing: '+k)
    manifests = {'apiVersion':'v1','kind':'List','items':[
        {'apiVersion':'v1','kind':'Secret','metadata':{'name':'mongo-keyfile','namespace':'exercise13'},
         'type':'Opaque','data':{'keyfile':base64.b64encode(key.read_bytes()).decode()}},
        {'apiVersion':'v1','kind':'Secret','metadata':{'name':'mongo-auth','namespace':'exercise13'},
         'type':'Opaque','stringData':values}]}
    (secret_dir/'k8s-secrets.json').write_text(json.dumps(manifests), encoding='utf-8')
    print('Credentials ready. Same key reused on all members. Values intentionally not printed.')


def client(role='admin', direct=None, authenticated=True):
    from pymongo import MongoClient
    # A sequential classroom workload with one observer thread. Leave pool defaults intact.
    # Short timeouts bound each local test attempt; outer polling tolerates elections/startup.
    opts = dict(serverSelectionTimeoutMS=5000, connectTimeoutMS=3000, socketTimeoutMS=10000,
                appname='Exercise13', retryWrites=True)
    hosts = direct or os.getenv('MONGO_HOSTS','mongo1:27017,mongo2:27017,mongo3:27017')
    if direct: opts['directConnection'] = True
    else: opts['replicaSet'] = 'rs0'
    if authenticated:
        users={'admin':(os.environ['MONGO_ADMIN_USER'],os.environ['MONGO_ADMIN_PASSWORD']),
               'app':('labuser',os.environ['MONGO_APP_PASSWORD']),
               'monitor':('monitor',os.environ['MONGO_MONITOR_PASSWORD'])}
        opts.update(username=users[role][0],password=users[role][1],authSource='admin')
    return MongoClient('mongodb://'+hosts, **opts)


def summary(c):
    s=c.admin.command('replSetGetStatus')
    return [{'name':m['name'],'state':m['stateStr'],'health':m['health']} for m in s['members']]


def healthy(members):
    return (len(members)==3 and sum(m['state']=='PRIMARY' for m in members)==1
            and sum(m['state']=='SECONDARY' for m in members)==2 and all(m['health']==1 for m in members))


def wait_healthy(c, seconds=180):
    from pymongo.errors import PyMongoError
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:
            s=summary(c)
            if healthy(s): return s
        except PyMongoError: pass
        time.sleep(2)
    raise RuntimeError('Replica set did not reach one PRIMARY and two SECONDARY members.')


def verify():
    from pymongo.errors import OperationFailure
    from pymongo.write_concern import WriteConcern
    with client() as c, client('app') as app:
        members=wait_healthy(c)
        coll=app.exercise13.get_collection('checks',write_concern=WriteConcern(w=3,wtimeout=30000))
        token=secrets.token_hex(8)
        coll.replace_one({'_id':'compose-sentinel'},{'_id':'compose-sentinel','token':token},upsert=True)
        found=coll.find_one({'_id':'compose-sentinel'})
        denied=False
        # ping/hello can work without authentication. A protected collection read must fail.
        with client(authenticated=False) as anonymous:
            try: anonymous.exercise13.checks.find_one({})
            except OperationFailure as exc:
                if exc.code==13: denied=True
                else: raise
        result={'lab':'13.1','timestamp':utc(),'members':members,'writeConcern':'w=3',
                'authenticated_read_write':found['token']==token,'unauthenticated_read_denied':denied}
        result['passed']=healthy(members) and result['authenticated_read_write'] and denied
        save('lab13_1_health.json',result)
        if not result['passed']: raise RuntimeError('Health/authentication checks failed.')


def failover():
    from pymongo.errors import PyMongoError, AutoReconnect, OperationFailure
    from pymongo.write_concern import WriteConcern
    with client() as admin, client('app') as app:
        before=wait_healthy(admin)
        old=next(m['name'] for m in before if m['state']=='PRIMARY')
        coll=app.exercise13.get_collection('failover',write_concern=WriteConcern(w='majority',wtimeout=10000))
        run=secrets.token_hex(8)
        coll.insert_one({'_id':run+'-sentinel','value':'preserved'})
        samples=[]; stop=threading.Event()
        def observe():
            seq=0
            while not stop.is_set():
                sample={'timestamp':utc(),'sequence':seq}
                try:
                    coll.replace_one({'_id':f'{run}-{seq}'},{'_id':f'{run}-{seq}','sequence':seq},upsert=True)
                    sample['read_ok']=coll.find_one({'_id':run+'-sentinel'})['value']=='preserved'
                    sample['write_ok']=True
                except PyMongoError as exc:
                    sample.update(read_ok=False,write_ok=False,error_type=type(exc).__name__)
                samples.append(sample); seq+=1; stop.wait(0.5)
        worker=threading.Thread(target=observe,daemon=True); worker.start()
        time.sleep(3)
        step_at=utc(); started=time.monotonic(); new=None; command_ok=False
        try:
            with client(direct=old) as primary:
                try:
                    primary.admin.command({'replSetStepDown':60,'secondaryCatchUpPeriodSecs':15})
                    command_ok=True
                except AutoReconnect:
                    # Stepping down can close the command connection; verify the new election below.
                    command_ok=True
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                try:
                    current=summary(admin)
                    new=next((m['name'] for m in current if m['state']=='PRIMARY' and m['name']!=old),None)
                    if new: break
                except PyMongoError: pass
                time.sleep(1)
            elapsed=round(time.monotonic()-started,3)
            if not new: raise RuntimeError('No different primary elected within 90 seconds.')
            time.sleep(5)
        finally:
            stop.set(); worker.join(timeout=30)
        if worker.is_alive(): raise RuntimeError('Observer did not stop.')
        after=wait_healthy(admin)
        acknowledged=[s for s in samples if s.get('write_ok')]
        preserved=all(coll.find_one({'_id':f"{run}-{s['sequence']}"}) is not None for s in acknowledged)
        post=[s for s in samples if s['timestamp']>step_at and s.get('write_ok') and s.get('read_ok')]
        result={'lab':'13.1 failover','timestamp':utc(),'old_primary':old,'new_primary':new,
                'stepdown_requested_at':step_at,'election_observed_seconds':elapsed,
                'successful_samples':len(acknowledged),'transient_failures':len(samples)-len(acknowledged),
                'post_stepdown_successes':len(post),'acknowledged_documents_preserved':preserved,
                'members_after':after,'samples':samples}
        result['passed']=command_ok and old!=new and len(post)>0 and preserved and healthy(after)
        save('lab13_1_failover.json',result)
        if not result['passed']: raise RuntimeError('Failover test failed.')


def exporter():
    from prometheus_client import Gauge, start_http_server
    from pymongo.errors import PyMongoError
    up=Gauge('mongodb_up','One when a MongoDB serverStatus scrape succeeds')
    connections=Gauge('mongodb_connections','Connections reported by MongoDB',['kind'])
    ops=Gauge('mongodb_opcounters','Cumulative operations reported by MongoDB',['operation'])
    state=Gauge('mongodb_member_state','Replica set numeric state: 1 primary, 2 secondary',['member'])
    start_http_server(9216)
    with client('monitor',direct='mongo1:27017') as c:
        while True:
            try:
                s=c.admin.command('serverStatus')
                for key,value in s['connections'].items():
                    if isinstance(value,(int,float)): connections.labels(key).set(value)
                for key,value in s['opcounters'].items(): ops.labels(key).set(value)
                rs=c.admin.command('replSetGetStatus')
                for m in rs['members']: state.labels(m['name']).set(m['state'])
                up.set(1)
            except PyMongoError: up.set(0)
            time.sleep(3)


def metrics():
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        try:
            raw=urlopen('http://exporter:9216/metrics',timeout=5).read().decode()
            targets=json.load(urlopen('http://prometheus:9090/api/v1/targets',timeout=5))
            query=json.load(urlopen('http://prometheus:9090/api/v1/query?query=mongodb_up',timeout=5))
            targets_ok=any(t.get('health')=='up' and t['labels'].get('job')=='mongodb'
                           for t in targets['data']['activeTargets'])
            data_ok=any(v['value'][1]=='1' for v in query['data']['result'])
            if 'mongodb_up 1.0' in raw and targets_ok and data_ok:
                Path(os.getenv('RESULTS_DIR','/results'),'metrics.txt').write_text(raw)
                save('lab13_1_monitoring.json',{'timestamp':utc(),'passed':True,'exporter_up':True,
                      'prometheus_target_up':True,'prometheus_mongodb_up':1,
                      'exporter_url':'http://localhost:9216/metrics','prometheus_url':'http://localhost:9090'})
                return
        except (OSError,ValueError,KeyError): pass
        time.sleep(3)
    save('lab13_1_monitoring.json',{'timestamp':utc(),'passed':False})
    raise RuntimeError('Monitoring did not become healthy within 90 seconds.')


def export(destination):
    root=Path(destination); root.mkdir(parents=True,exist_ok=True)
    if any(root.iterdir()): raise RuntimeError('Export destination must be empty to avoid overwriting work.')
    source=Path('/kit')
    for name in ['scripts','k8s','terraform','monitoring','docs']:
        shutil.copytree(source/name,root/name)
    for pattern in ['*.ps1','*.yml','README.md','requirements.txt','Dockerfile','.dockerignore','.gitignore']:
        for f in source.glob(pattern): shutil.copy2(f,root/f.name)
    (root/'results').mkdir()
    print('Clean demonstration kit exported. Generate new credentials and new evidence with START.ps1 -UsePublishedImage.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','verify','failover','exporter','metrics','export','help'])
    parser.add_argument('--destination',default='/work')
    a=parser.parse_args()
    if a.action in ['prepare','export']: globals()[a.action](a.destination)
    elif a.action=='help': parser.print_help()
    else: globals()[a.action]()


if __name__=='__main__':
    try: main()
    except Exception as exc:
        # Connection exceptions can contain host/user information; never dump credential-bearing URIs.
        print('ERROR:',type(exc).__name__,str(exc) if isinstance(exc,RuntimeError) else 'Check service status and the troubleshooting guide.',file=sys.stderr)
        sys.exit(1)
