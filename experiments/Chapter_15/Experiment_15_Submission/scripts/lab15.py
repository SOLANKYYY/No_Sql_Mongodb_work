"""Live HTTP security checks and five-tenant collection migration with measured comparisons."""
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import statistics, secrets
from core import *

def http(method,path,token=None,data=None):
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    req=Request('http://api:8000'+path,data=json.dumps(data).encode() if data is not None else None,headers=headers,method=method)
    try:
        with urlopen(req,timeout=30) as r:return r.status,json.loads(r.read() or b'null')
    except HTTPError as e:return e.code,json.loads(e.read() or b'null')

def api_test():
    deadline=time.monotonic()+120
    while True:
        try:
            if http('GET','/health')[0]==200:break
        except Exception:pass
        if time.monotonic()>deadline:raise RuntimeError('API not healthy within 120 seconds.')
        time.sleep(2)
    with client() as c:
        # Reset only the dedicated lab API data for a repeatable assessment run.
        c.exercise15_api.tasks.delete_many({});c.exercise15_api.rate_limits.delete_many({})
    tokens={}
    for user in ['alice','bob','carol','admin-a','admin-b','rateuser']:
        status,response=http('POST','/auth/token',data={'username':user,'password':os.environ['DEMO_PASSWORD']})
        if status!=200:raise RuntimeError('Demo login failed. Keep the original .env when reusing database volumes.')
        tokens[user]=response['access_token']
    checks={}
    checks['unauthenticated_rejected']=http('GET','/tasks')[0]==401
    checks['invalid_token_rejected']=http('GET','/tasks','invalid')[0]==401
    ids={}
    for user in ['alice','bob','carol']:
        status,data=http('POST','/tasks',tokens[user],{'title':user+' task','priority':'high'})
        checks[user+'_created']=status==201;ids[user]=data['id']
    checks['body_tenant_spoof_rejected']=http('POST','/tasks',tokens['alice'],{'title':'spoof','tenant_id':'tenant-b'})[0]==422
    checks['own_task_read']=http('GET','/tasks/'+ids['alice'],tokens['alice'])[0]==200
    checks['same_tenant_other_owner_hidden']=http('GET','/tasks/'+ids['bob'],tokens['alice'])[0]==404
    checks['tenant_admin_reads_all_own_tenant']=len(http('GET','/tasks',tokens['admin-a'])[1])==2
    checks['regular_list_only_own']=len(http('GET','/tasks',tokens['alice'])[1])==1
    for method,data in [('GET',None),('PATCH',{'status':'completed'}),('DELETE',None)]:
        checks['cross_tenant_'+method.lower()+'_blocked']=http(method,'/tasks/'+ids['alice'],tokens['admin-b'],data)[0]==404
    checks['admin_updates_other_owner']=http('PATCH','/tasks/'+ids['bob'],tokens['admin-a'],{'status':'completed'})[0]==200
    checks['regular_updates_own']=http('PATCH','/tasks/'+ids['alice'],tokens['alice'],{'priority':'low'})[0]==200
    checks['owner_spoof_update_rejected']=http('PATCH','/tasks/'+ids['alice'],tokens['alice'],{'owner_id':'bob'})[0]==422
    checks['own_delete']=http('DELETE','/tasks/'+ids['alice'],tokens['alice'])[0]==204
    # Avoid a fixed-window boundary during the concurrency drill.
    remaining=60-time.time()%60
    if remaining<20:time.sleep(remaining+0.2)
    with client() as c:c.exercise15_api.rate_limits.delete_many({'_id':{'$regex':'^tenant-rate:rateuser:'}})
    with ThreadPoolExecutor(max_workers=8) as pool:
        codes=list(pool.map(lambda _:http('GET','/tasks',tokens['rateuser'])[0],range(30)))
    counts={'allowed_200':codes.count(200),'limited_429':codes.count(429),'other':len([x for x in codes if x not in (200,429)])}
    checks['atomic_rate_limit']=counts=={'allowed_200':20,'limited_429':10,'other':0}
    result={'timestamp':utc(),'passed':all(checks.values()),'checks':checks,'concurrent_rate_limit':counts,'request_limit':20,'window_seconds':60,
            'identity_source':'validated JWT plus server-side user record','rbac':'admin: all tasks within own tenant; user: own tasks only','api_url':'http://localhost:8015/docs'}
    save('lab15_1_api.json',result)
    if not result['passed']:raise RuntimeError('API isolation/RBAC/rate-limit check failed.')

def digest_docs(docs):
    from bson.json_util import dumps,CANONICAL_JSON_OPTIONS
    text='\n'.join(dumps(x,json_options=CANONICAL_JSON_OPTIONS,sort_keys=True) for x in sorted(docs,key=lambda d:d['_id']))
    return hashlib.sha256(text.encode()).hexdigest()

def copy_tenant(db,tenant):
    if not re.fullmatch(r'tenant_[0-4]',tenant):raise ValueError('Unknown lab tenant')
    name='tasks_'+tenant
    if name not in db.list_collection_names():
        db.create_collection(name,validator={'$jsonSchema':{'bsonType':'object','required':['tenant_id'],'properties':{'tenant_id':{'enum':[tenant]}}}})
    target=db[name];target.create_index('created_at')
    docs=list(db.tasks.find({'tenant_id':tenant}))
    for d in docs:target.replace_one({'_id':d['_id']},d,upsert=True)
    found=list(target.find({}))
    return {'tenant':tenant,'source_count':len(docs),'target_count':len(found),'source_sha256':digest_docs(docs),'target_sha256':digest_docs(found),
            'no_cross_tenant_documents':all(x['tenant_id']==tenant for x in found),'passed':len(docs)==len(found) and digest_docs(docs)==digest_docs(found) and all(x['tenant_id']==tenant for x in found)}

def timing(fn,repeats=20):
    fn();values=[]
    for _ in range(repeats):
        t=time.perf_counter();fn();values.append((time.perf_counter()-t)*1000)
    return {'repeats':repeats,'median_ms':statistics.median(values),'mean_ms':statistics.mean(values),'min_ms':min(values),'max_ms':max(values)}

def migration():
    tenants=[f'tenant_{i}' for i in range(5)]
    with client() as c:
        db=c.exercise15_migration
        for name in ['tasks']+['tasks_'+x for x in tenants]:db[name].drop()
        stamp=datetime.now(timezone.utc)
        db.tasks.insert_many([{'_id':f'{tenant}:{i:03}','tenant_id':tenant,'title':f'Task {i}','status':'open','priority':'medium','created_at':stamp} for tenant in tenants for i in range(100)])
        db.tasks.create_index([('tenant_id',1),('created_at',1)])
        baseline=digest_docs(list(db.tasks.find({})));first=[copy_tenant(db,t) for t in tenants];second=[copy_tenant(db,t) for t in tenants]
        def shared_counts():return list(db.tasks.aggregate([{'$group':{'_id':'$tenant_id','count':{'$sum':1}}},{'$sort':{'_id':1}}]))
        def dedicated_counts():return [{'_id':t,'count':db['tasks_'+t].count_documents({})} for t in tenants]
        comparison={'list_one_tenant':{'shared':timing(lambda:list(db.tasks.find({'tenant_id':'tenant_0'}).sort('created_at',1))),
                                     'collection_per_tenant':timing(lambda:list(db.tasks_tenant_0.find({}).sort('created_at',1)))},
                    'cross_tenant_counts':{'shared':timing(shared_counts),'collection_per_tenant':timing(dedicated_counts)}}
        def create_timing(col,tenant):
            samples=[]
            for i in range(21):
                key='benchmark:'+secrets.token_hex(12)
                started=time.perf_counter()
                col.insert_one({'_id':key,'tenant_id':tenant,'title':'benchmark','created_at':stamp})
                elapsed=(time.perf_counter()-started)*1000
                col.delete_one({'_id':key,'tenant_id':tenant})  # Cleanup is outside the measured insertion.
                if i:samples.append(elapsed)
            return {'repeats':20,'median_ms':statistics.median(samples),'mean_ms':statistics.mean(samples),'min_ms':min(samples),'max_ms':max(samples)}
        comparison['create_task']={'shared':create_timing(db.tasks,'tenant_0'),'collection_per_tenant':create_timing(db.tasks_tenant_0,'tenant_0')}
        # Preserve the source; demonstrate rollback for one target and then reconstruct it.
        db.tasks_tenant_4.drop();rollback_ok=digest_docs(list(db.tasks.find({})))==baseline;copy_tenant(db,'tenant_4')
        counts_equal=shared_counts()==dedicated_counts()
        result={'timestamp':utc(),'tenants':5,'documents_per_tenant':100,'total_documents':500,'first_copy':first,'repeat_copy':second,'idempotent':first==second,
                'source_unchanged':digest_docs(list(db.tasks.find({})))==baseline,'rollback_source_preserved':rollback_ok,'aggregate_counts_equal':counts_equal,'timings':comparison,
                'passed':all(r['passed'] for r in first+second) and first==second and rollback_ok and counts_equal and digest_docs(list(db.tasks.find({})))==baseline,
                'scope':'offline lab copy with no concurrent writers; application cutover is not performed'}
        save('lab15_2_migration.json',result)
        if not result['passed']:raise RuntimeError('Tenant migration validation failed.')
