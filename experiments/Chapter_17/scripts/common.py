import json, os, platform, sys, time, hashlib
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
RESULTS=Path(os.getenv('RESULTS_DIR','/results'))
def save(name,data):
    RESULTS.mkdir(parents=True,exist_ok=True)
    tmp=RESULTS/(name+'.tmp')
    tmp.write_text(json.dumps(data,indent=2,default=str),encoding='utf-8')
    tmp.replace(RESULTS/name)
def load(name): return json.loads((RESULTS/name).read_text(encoding='utf-8-sig'))
def now(): return datetime.now(timezone.utc).isoformat()
def fingerprint(value): return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()
def environment():
    from importlib.metadata import version, PackageNotFoundError
    packages={}
    for name in ['pymongo','cassandra-driver','neo4j','fastembed','faiss-cpu','transformers','torch']:
        try: packages[name]=version(name)
        except PackageNotFoundError: pass
    return {'python':sys.version,'platform':platform.platform(),'cpu_count':os.cpu_count(),'packages':packages}
def mongo():
    from pymongo import MongoClient
    # One sequential lab client; use default pool. Fail startup discovery within 30s.
    c=MongoClient(os.environ['MONGO_URI'],serverSelectionTimeoutMS=30000)
    c.admin.command('ping')
    return c
