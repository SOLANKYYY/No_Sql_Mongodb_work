import csv, hashlib, json, os
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests
FIELDS=['id','source','target','type','timestamp','indicator']

def normalize(row,mapping=None):
    mapping=mapping or {k:k for k in FIELDS}
    d={k:row.get(mapping.get(k,k)) for k in FIELDS}
    for k,v in d.items():
        if v is None or not str(v).strip(): raise ValueError('Missing required field: '+k)
        d[k]=str(v).strip()
    t=datetime.fromisoformat(d['timestamp'].replace('Z','+00:00'))
    if t.tzinfo is None: raise ValueError('Timestamp must include timezone: '+d['id'])
    if t>datetime.now(timezone.utc): raise ValueError('Future timestamp: '+d['id'])
    d['timestamp']=t.astimezone(timezone.utc).isoformat(timespec='milliseconds')
    d['day']=d['timestamp'][:10]
    return d

def read_export(path):
    with path.open(encoding='utf-8-sig') as f:
        if path.suffix=='.csv': yield from csv.DictReader(f)
        elif path.suffix=='.jsonl':
            for line in f:
                if line.strip(): yield json.loads(line)
        elif path.suffix=='.json':
            value=json.load(f)
            if isinstance(value,list): yield from value
            else: yield from value['records']
        else: raise ValueError('Export must be CSV, JSONL or JSON')

def api_records(url):
    # API contract: JSON list, or {records:[...], next:"absolute HTTPS URL"|null}.
    # Keep credentials in .env; never include URLs with tokens in saved provenance.
    if urlparse(url).scheme!='https': raise ValueError('API must use HTTPS')
    origin=urlparse(url).netloc
    headers={}
    if os.getenv('THREAT_API_TOKEN'): headers['Authorization']='Bearer '+os.environ['THREAT_API_TOKEN']
    seen=set()
    for _ in range(2000):
        if url in seen: raise ValueError('Pagination loop detected')
        seen.add(url)
        if urlparse(url).scheme!='https' or urlparse(url).netloc!=origin: raise ValueError('Pagination must stay on the same HTTPS host')
        response=requests.get(url,headers=headers,timeout=60,allow_redirects=False)
        if response.status_code!=200: raise RuntimeError('Threat API returned HTTP '+str(response.status_code))
        payload=response.json()
        if isinstance(payload,list): yield from payload;return
        yield from payload['records']
        url=payload.get('next')
        if not url: return
    raise ValueError('API exceeded 2000 pages; export the records to a local file')

def load_dataset(directory=Path('/data')):
    mapping_path=directory/'field_mapping.json'
    mapping=json.loads(mapping_path.read_text()) if mapping_path.exists() else None
    provenance_path=directory/'source.json'
    if not provenance_path.exists(): raise ValueError('Add data/source.json with source_name and collected_at. See data/README.md. No generated data will be substituted.')
    provenance=json.loads(provenance_path.read_text())
    if not provenance.get('source_name') or not provenance.get('collected_at'): raise ValueError('source.json requires source_name and collected_at')
    collected=datetime.fromisoformat(provenance['collected_at'].replace('Z','+00:00'))
    if collected.tzinfo is None or collected>datetime.now(timezone.utc): raise ValueError('collected_at must be a valid past UTC/offset timestamp')
    paths=[directory/('threats'+ext) for ext in ['.jsonl','.csv','.json'] if (directory/('threats'+ext)).exists()]
    url=os.getenv('THREAT_API_URL','').strip()
    if len(paths)>1: raise ValueError('Keep only one threats export file in data/')
    if paths:
        path=paths[0];iterator=read_export(path)
        raw_sha=hashlib.sha256(path.read_bytes()).hexdigest();mode='user-supplied export'
    elif url: iterator=api_records(url);raw_sha=None;mode='HTTPS API'
    else: raise ValueError('Provide data/threats.jsonl, .csv or .json, or set THREAT_API_URL in .env')
    unique={};duplicates=0
    for raw in iterator:
        d=normalize(raw,mapping)
        if d['id'] in unique:
            if unique[d['id']]!=d: raise ValueError('Conflicting duplicate record ID: '+d['id'])
            duplicates+=1
        unique[d['id']]=d
    if len(unique)<1000: raise ValueError(f'Need at least 1,000 unique records for the reduced lab; found {len(unique):,}. Do not pad or duplicate records.')
    rows=sorted(unique.values(),key=lambda x:(x['timestamp'],x['id']),reverse=True)[:15000]
    sources=sorted({d['source'] for d in rows})
    if len(sources)<2: raise ValueError('The selected records must cover multiple sources')
    fingerprint=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
    metadata={'mode':mode,'source_name':provenance['source_name'],'collected_at':provenance['collected_at'],
      'origin_attestation':provenance.get('origin_attestation','User-supplied source; authenticity not independently verified'),
      'raw_export_sha256':raw_sha,'normalized_sha256':fingerprint,'available_unique':len(unique),'selected':len(rows),
      'duplicates_removed':duplicates,'sources':len(sources),'oldest':rows[-1]['timestamp'],'newest':rows[0]['timestamp'],
      'selection':'Up to 15,000 most recent supplied records; partial feed coverage',
      'assignment_requested':100000,'adaptation':'User-requested reduced workload; does not satisfy the original 100,000-record requirement',
      'record_unit':provenance.get('record_unit','user-supplied record'),
      'timestamp_basis':provenance.get('timestamp_basis','supplied timestamp'),
      'target_basis':provenance.get('target_basis','supplied target')}
    return rows,metadata
