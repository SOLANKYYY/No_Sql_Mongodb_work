"""30-second live metrics plus explicitly labelled webhook/threshold drills."""
import json,os,time,threading
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import URLError
from core import *

def collect(c,previous=None):
    from pymongo.errors import OperationFailure
    s=c.admin.command('serverStatus');wt=s.get('wiredTiger',{}).get('cache',{})
    m={'timestamp':utc(),'uptime':s.get('uptime'),'connections':s.get('connections',{}),'opcounters':s.get('opcounters',{}),
       'cache_bytes':wt.get('bytes currently in the cache'),'cache_max_bytes':wt.get('maximum bytes configured'),
       'cache_dirty_bytes':wt.get('tracked dirty bytes in the cache'),'pages_read':wt.get('pages read into cache'),
       'pages_requested':wt.get('pages requested from the cache')}
    m['cache_hit_percent']=cache_hit(previous,m)
    try:m['members'],m['replication_lag_seconds']=replica_details(c.admin.command('replSetGetStatus'))
    except OperationFailure as exc:
        if exc.code not in (76,123):raise
        m['members']=[];m['replication_lag_seconds']={};m['replica_note']='Standalone; replica metrics not applicable.'
    if not m['replication_lag_seconds']:m['replica_note']='No secondary member; lag is N/A, not zero.'
    m['alerts']=alerts_for(m)
    return m

def send_webhook(url,alerts,synthetic=False):
    if not url:return {'configured':False,'delivered':False}
    message=('EXERCISE 14 TEST FIXTURE - ' if synthetic else 'Exercise 14 - ')+'\n'.join(alerts)
    payload={'text':message,'content':message}
    try:
        request=Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','User-Agent':'Exercise14/1.0'},method='POST')
        with urlopen(request,timeout=10) as response:code=response.status
        return {'configured':True,'delivered':200<=code<300,'status_code':code}
    except Exception as exc:
        # Exception strings can contain webhook secret URLs; record only the error class.
        return {'configured':True,'delivered':False,'error_type':type(exc).__name__}

def display(m):
    print('\nMongoDB monitoring | '+m['timestamp'],flush=True)
    rows=[('Connections current',m['connections'].get('current')),('Connections available',m['connections'].get('available'))]
    rows += [('Operations '+k,v) for k,v in m['opcounters'].items()]
    rows += [('Cache bytes / maximum',f"{m['cache_bytes']} / {m['cache_max_bytes']}"),('Dirty cache bytes',m['cache_dirty_bytes']),
             ('Cache hit estimate', 'N/A (first, idle or reset interval)' if m['cache_hit_percent'] is None else f"{m['cache_hit_percent']:.2f}%"),
             ('Replica members',', '.join(x['name']+' '+x['state'] for x in m['members'])),('Secondary lag (seconds)',m['replication_lag_seconds'] or 'N/A (no secondary)')]
    for label,value in rows:print(f'{label:28} | {value}',flush=True)
    for alert in m['alerts']:print(alert,flush=True)

def monitor(samples=3,interval=30,uri=SOURCE):
    if interval<=0 or samples<0:raise ValueError('Positive interval and non-negative sample count required.')
    previous=None;records=[];i=0;started=time.monotonic()
    with client(uri) as c:
        while samples==0 or i<samples:
            tick=time.monotonic();m=collect(c,previous);display(m)
            if m['alerts']:m['webhook']=send_webhook(os.getenv('WEBHOOK_URL',''),m['alerts'])
            append(LOGS/'metrics.log',m);previous=m;i+=1
            if samples:records.append(m)
            if samples and i>=samples:break
            time.sleep(max(0,interval-(time.monotonic()-tick)))
    result={'timestamp':utc(),'passed':len(records)>=3 and interval==30 and all(x['connections'].get('current') is not None and x['cache_max_bytes'] for x in records),
            'interval_seconds':interval,'elapsed_seconds':round(time.monotonic()-started,3),'samples':records,'sample_count':len(records),'source':'live MongoDB serverStatus / replSetGetStatus'}
    save('lab14_1_monitoring.json',result)
    if not result['passed']:raise RuntimeError('Submission needs at least three live samples at 30-second intervals.')

def alert_test(external=False):
    # Fixtures test threshold logic; they are never labelled as observed server faults.
    received=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))));self.send_response(200);self.end_headers();self.wfile.write(b'OK')
        def log_message(self,*args):pass
    server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    fixture={'cache_hit_percent':70.0,'replication_lag_seconds':{'fixture-secondary:27017':12.0}}
    alerts=alerts_for(fixture)
    try:delivery=send_webhook(f'http://127.0.0.1:{server.server_port}/alerts',alerts,True)
    finally:server.shutdown();server.server_close();thread.join()
    healthy=alerts_for({'cache_hit_percent':80.0,'replication_lag_seconds':{'fixture-secondary':10.0}})
    result={'timestamp':utc(),'evidence_type':'synthetic threshold fixture + real local HTTP POST','fixture':fixture,'alerts':alerts,
            'boundary_values_do_not_alert':not healthy,'local_delivery':delivery,'received_payloads':received,
            'passed':len(alerts)==2 and not healthy and delivery['delivered'] and len(received)==1}
    if external:
        url=os.getenv('WEBHOOK_URL','')
        if not url:raise RuntimeError('Set WEBHOOK_URL privately in .env first.')
        result['external_delivery']=send_webhook(url,alerts,True)
        result['passed']=result['passed'] and result['external_delivery']['delivered']
    save('lab14_1_webhook.json',result)
    if not result['passed']:raise RuntimeError('Webhook test failed.')
