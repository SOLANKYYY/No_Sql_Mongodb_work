import json, os, platform, sys
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
RESULTS=Path(os.getenv('RESULTS_DIR','/results'))
EXPERIMENT=11
def now():return datetime.now(timezone.utc).isoformat()
def save(name,value):
 RESULTS.mkdir(parents=True,exist_ok=True)
 p=RESULTS/name;t=p.with_suffix('.tmp');t.write_text(json.dumps(value,indent=2,default=str),encoding='utf-8');t.replace(p)
def load(name):return json.loads((RESULTS/name).read_text(encoding='utf-8-sig'))
def environment():
 from importlib.metadata import version
 return {'python':sys.version,'platform':platform.platform(),'pymongo':version('pymongo'),'mongo_image':'mongo:7.0.16','scope':'isolated educational lab'}
