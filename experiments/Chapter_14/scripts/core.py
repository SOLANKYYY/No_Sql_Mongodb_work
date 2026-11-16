"""Exercise 14 support code. Destructive drills are confined to the bundled lab hosts."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib, json, os, re, shutil, subprocess, time
from urllib.parse import urlparse

RESULTS=Path(os.getenv('RESULTS_DIR','/results'))
LOGS=Path(os.getenv('LOGS_DIR','/logs'))
BACKUPS=Path(os.getenv('BACKUP_DIR','/backups'))
SOURCE='mongodb://mongo:27017/?replicaSet=rs14'
TARGET='mongodb://mongo-restore:27017/?directConnection=true'
DB='exercise14'

def utc(): return datetime.now(timezone.utc).isoformat()
def write_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(data,indent=2,default=str)+'\n',encoding='utf-8');temp.replace(path)
def save(name,data):
    write_json(RESULTS/name,data);print(json.dumps(data,indent=2,default=str),flush=True)
def append(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as f:f.write(json.dumps(data,default=str)+'\n')
def client(uri=SOURCE):
    from pymongo import MongoClient
    # Sequential local classroom workload: retain normal pool defaults and reuse the client.
    # Fail server selection after 10s so scripts report a stopped local container promptly.
    # Do not constrain socket time: 100k-document verification may take time on a laptop.
    return MongoClient(uri,serverSelectionTimeoutMS=10000,appname='Exercise14',tz_aware=True)
def assert_lab(uri):
    if uri not in (SOURCE,TARGET):raise ValueError('Destructive drills only support the dedicated bundled lab hosts.')
def checksum(collection):
    from bson.json_util import dumps, CANONICAL_JSON_OPTIONS
    h=hashlib.sha256();count=0
    for doc in collection.find({}).sort('_id',1):
        h.update(dumps(doc,json_options=CANONICAL_JSON_OPTIONS,sort_keys=True,separators=(',',':')).encode());h.update(b'\n');count+=1
    return {'count':count,'sha256':h.hexdigest()}
def run_tool(exe,uri,args):
    # Password-bearing URIs, if a caller supplies one to backup-only CLI, stay in a private config.
    import tempfile
    cfg=None
    try:
        with tempfile.NamedTemporaryFile('w',suffix='.yml',delete=False) as f:
            cfg=Path(f.name);f.write('uri: '+json.dumps(uri)+'\n')
        cfg.chmod(0o600);start=time.perf_counter()
        done=subprocess.run([exe,'--config',str(cfg),*map(str,args)],capture_output=True,text=True)
        elapsed=time.perf_counter()-start
        # Do not print complete commands, URIs or unredacted tool errors.
        text=(done.stdout+'\n'+done.stderr).replace(uri,'[connection redacted]')
        text=re.sub(r'mongodb(?:\+srv)?://[^\s\"\']+','[connection redacted]',text)
        append(LOGS/'database-tools.jsonl',{'timestamp':utc(),'tool':exe,'exit_code':done.returncode,'seconds':elapsed,'output':text[-16000:]})
        if done.returncode:raise RuntimeError(exe+' failed; see logs/database-tools.jsonl')
        return elapsed
    finally:
        if cfg:cfg.unlink(missing_ok=True)
def backup_once(uri=SOURCE,root=BACKUPS,db=DB):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    folder=root/('backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir()
    started=utc()
    seconds=run_tool('mongodump',uri,['--db',db,'--gzip','--out',folder/'dump'])
    manifest={'kind':'exercise14-backup','completed':True,'started_at':started,'completed_at':utc(),'database':db,'seconds':seconds,'bytes':sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())}
    write_json(folder/'manifest.json',manifest)
    return folder,manifest

def retention(root,now=None,days=7):
    """Only remove completed owned backups. Never follow symlinks or delete arbitrary folders."""
    if days<1:raise ValueError('Retention must be at least one day.')
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True);now=now or datetime.now(timezone.utc)
    cutoff=now-timedelta(days=days);removed=[]
    for path in root.iterdir():
        if path.is_symlink() or not path.is_dir() or not re.fullmatch(r'backup-\d{8}T\d{12}Z',path.name):continue
        manifest=path/'manifest.json'
        if manifest.is_symlink() or not manifest.is_file():continue
        try:
            data=json.loads(manifest.read_text());stamp=datetime.fromisoformat(data['completed_at'])
            if data.get('kind')!='exercise14-backup' or data.get('completed') is not True or stamp.tzinfo is None:continue
        except (ValueError,KeyError,TypeError):continue
        if stamp<cutoff:
            shutil.rmtree(path);removed.append(path.name)
    return removed

def cache_hit(previous,current):
    """Interval estimate from WiredTiger page counters; cache occupancy is a different metric."""
    if previous is None or previous.get('uptime',0)>current.get('uptime',0):return None
    names=('pages_requested','pages_read')
    if any(previous.get(k) is None or current.get(k) is None for k in names):return None
    requests=current['pages_requested']-previous['pages_requested'];reads=current['pages_read']-previous['pages_read']
    if requests<=0 or reads<0 or reads>requests:return None
    return 100.0*(1.0-reads/requests)

def replica_details(status):
    members=status.get('members',[]);primaries=[x for x in members if x.get('stateStr')=='PRIMARY']
    primary_time=primaries[0].get('optimeDate') if primaries else None
    lags={}
    for m in members:
        if m.get('stateStr')=='SECONDARY':
            t=m.get('optimeDate');lags[m['name']]=max(0.0,(primary_time-t).total_seconds()) if isinstance(primary_time,datetime) and isinstance(t,datetime) else None
    return [{'name':m['name'],'state':m.get('stateStr'),'health':m.get('health')} for m in members],lags

def alerts_for(metric):
    alerts=[];hit=metric.get('cache_hit_percent')
    if hit is not None and hit<80:alerts.append(f'WARNING: cache hit estimate {hit:.2f}% is below 80%.')
    for member,lag in metric.get('replication_lag_seconds',{}).items():
        if lag is not None and lag>10:alerts.append(f'WARNING: replication lag on {member} is {lag:.2f}s (>10s).')
    return alerts
