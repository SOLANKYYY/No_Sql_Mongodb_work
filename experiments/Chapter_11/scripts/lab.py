"""Two real shards; measured routing and statistics, never simulated shard counts."""
import os,time,json,collections
from datetime import datetime,timedelta,timezone
from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import OperationFailure,ConnectionFailure
from common import save,now,environment

HOSTS={'cfg':os.getenv('CONFIG_HOST','config:27017'),'shardA':os.getenv('SHARD1_HOST','shard1:27017'),'shardB':os.getenv('SHARD2_HOST','shard2:27017')}
URI=os.getenv('MONGO_URI','mongodb://mongos:27017')
DB='exercise11'

def connect(host,direct=False):
    # Sequential local lab; keep default pool, fail discovery promptly on stopped services.
    return MongoClient(host,directConnection=direct,serverSelectionTimeoutMS=5000)

def bootstrap():
    for rs,host in HOSTS.items():
        with connect(host,True) as c:
            try:c.admin.command('replSetGetStatus')
            except OperationFailure as e:
                if e.code!=94:raise
                config={'_id':rs,'members':[{'_id':0,'host':host}]}
                if rs=='cfg':config['configsvr']=True
                c.admin.command('replSetInitiate',config)
            deadline=time.monotonic()+120
            while time.monotonic()<deadline:
                try:
                    if c.admin.command('hello').get('isWritablePrimary'):break
                except ConnectionFailure:pass
                time.sleep(1)
            else:raise RuntimeError('No PRIMARY for '+rs)
            actual=c.admin.command('replSetGetConfig')['config']
            if actual['_id']!=rs or actual['members'][0]['host']!=host:raise ValueError('Replica configuration does not match this kit')
            print(rs,'PRIMARY ready',flush=True)

def register():
    with connect(URI) as c:
        if c.admin.command('hello').get('msg')!='isdbgrid':raise ValueError('Connect to mongos, not a standalone mongod')
        existing={s['_id'] for s in c.admin.command('listShards')['shards']}
        for name in ('shardA','shardB'):
            if name not in existing:c.admin.command('addShard',name+'/'+HOSTS[name],name=name)
        print(json.dumps(c.admin.command('listShards'),default=str,indent=2))

def shard_names(value):
    found=set()
    if isinstance(value,dict):
        if isinstance(value.get('shardName'),str):found.add(value['shardName'])
        for item in value.values():found.update(shard_names(item))
    elif isinstance(value,list):
        for item in value:found.update(shard_names(item))
    return sorted(found)

def distribution(c,name):
    raw=c[DB].command('collStats',name,scale=1)
    shards={s:{'count':v.get('count',0),'size_bytes':v.get('size',0),'storage_bytes':v.get('storageSize',0)} for s,v in raw.get('shards',{}).items()}
    if not shards:raise AssertionError('No per-shard collStats returned')
    return {'shards':shards,'total_count':sum(x['count'] for x in shards.values()),'raw':raw}

def decision_matrix():
    customers=['VIP' if i<2000 else 'C'+str(i%1000) for i in range(10000)]
    freq=collections.Counter(customers)
    rows=[
      ['order_id',10000,'Unique, but sequential IDs concentrate new range inserts','Order lookup targets; customer queries broadcast','High cardinality does not guarantee even writes'],
      ['customer_id',len(freq),'Customer popularity can skew load','Customer equality and customer ranges can target','Keeps each customer together; a very large customer remains a hotspot'],
      ['order_date',10000,'Monotonic timestamps direct new writes to the upper chunk','Bounded date ranges can target relevant chunks','Useful for time-range locality, poor for evenly spreading new writes'],
      ['hashed customer_id',len(freq),'Hash spreads distinct customers; repeated VIP value stays together','Customer equality targets; customer ranges usually scatter','Recommended for many customers with mainly equality queries; monitor large tenants']]
    return {'workload':'10,000 synthetic orders: 2,000 VIP orders, 8,000 spread across 1,000 other customers',
      'max_customer_frequency':max(freq.values()),'rows':rows,
      'recommendation':'Hashed customer_id for customer-equality workload with many customers. Hashing does not divide a single hot customer across shards. Reconsider compound keys or application design if one tenant dominates.'}

def run():
    with connect(URI) as c:
        shards=c.admin.command('listShards')['shards']
        if {s['_id'] for s in shards}!={'shardA','shardB'}:raise ValueError('Expected the dedicated two-shard lab')
        old_mode=c.admin.command('balancerStatus')['mode']
        c.admin.command('balancerStop',maxTimeMS=120000)
        try:
            # Reset only this kit's dedicated educational database.
            c.drop_database(DB)
            c.admin.command('enableSharding',DB,primaryShard='shardA')
            d=c[DB];d.hotspot_data.create_index('ts');d.even_data.create_index([('user_id','hashed')])
            c.admin.command('shardCollection',DB+'.hotspot_data',key={'ts':1})
            c.admin.command('shardCollection',DB+'.even_data',key={'user_id':'hashed'},numInitialChunks=4)
            start=datetime(2025,1,1,tzinfo=timezone.utc);cutoff=start-timedelta(seconds=1)
            # Explicit, disclosed range placement makes a small dataset demonstrate the mechanism.
            # The empty old-history chunk moves to B; new timestamps fall in A's upper chunk.
            c.admin.command('split',DB+'.hotspot_data',middle={'ts':cutoff})
            c.admin.command('moveChunk',DB+'.hotspot_data',find={'ts':start-timedelta(days=1)},to='shardB',_waitForDelete=True)
            docs=[{'_id':i,'ts':start+timedelta(seconds=i),'user_id':ObjectId(f'{i+1:024x}'),'amount':(i%100)+1,'payload':'educational-order'} for i in range(10000)]
            times={}
            for name in ('hotspot_data','even_data'):
                t=time.perf_counter();d[name].insert_many(docs);times[name]=(time.perf_counter()-t)*1000
            stats={name:distribution(c,name) for name in ('hotspot_data','even_data')}
            for value in stats.values():assert value['total_count']==10000
            assert max(x['count'] for x in stats['hotspot_data']['shards'].values())==10000
            assert sum(x['count']>0 for x in stats['even_data']['shards'].values())==2
            lo=start+timedelta(seconds=600);hi=start+timedelta(seconds=1200)
            same_range={'ts':{'$gte':lo,'$lt':hi}}
            queries=[('timestamp range on ranged key','hotspot_data',same_range),
                     ('same timestamp range on hashed collection','even_data',same_range),
                     ('hashed equality','even_data',{'user_id':docs[1234]['user_id']}),
                     ('hashed user_id range','even_data',{'user_id':{'$gte':docs[600]['user_id'],'$lt':docs[1200]['user_id']}})]
            explanations=[]
            for label,name,query in queries:
                raw=d.command('explain',{'find':name,'filter':query},verbosity='executionStats')
                count=d[name].count_documents(query);targeted=shard_names(raw)
                if not targeted:raise AssertionError('Could not extract shard targeting from real explain')
                explanations.append({'label':label,'collection':name,'filter':query,'shards':targeted,'shard_count':len(targeted),'matched':count,'raw':raw})
            assert [x['matched'] for x in explanations]==[600,600,1,600]
            assert [x['shard_count'] for x in explanations]==[1,2,1,2]
            chunks=[]
            for name in ('hotspot_data','even_data'):
                metadata=c.config.collections.find_one({'_id':DB+'.'+name})
                chunks.append({'collection':name,'key':metadata['key'],'chunks':list(c.config.chunks.find({'uuid':metadata['uuid']},{'_id':0,'min':1,'max':1,'shard':1}))})
            evidence={'experiment':11,'passed':True,'at':now(),'environment':environment(),'server_version':c.admin.command('buildInfo')['version'],
              'topology':shards,'matrix':decision_matrix(),'distribution':stats,'explain':explanations,'chunk_layout':chunks,'insert_ms':times,
              'method':'10,000 identical synthetic documents per collection. Balancer paused only during measurement; timestamp upper-range ownership explicitly configured; hashed key uses MongoDB hash and four initial chunks. Single-member replica sets are for resource-limited demonstration, not HA.',
              'checks':{'counts':True,'ranged_hotspot':True,'hashed_spread':True,'routing_verified':True}}
            save('evidence.json',evidence);save('run_state.json',{'status':'passed','at':now()})
            print('SCREENSHOT 01: shard distribution')
            print(json.dumps({k:{'shards':v['shards'],'total_count':v['total_count']} for k,v in stats.items()},indent=2))
            print('SCREENSHOT 02: explain routing')
            print(json.dumps([{k:v for k,v in e.items() if k not in ('raw','filter')} for e in explanations],indent=2))
            print('EXERCISE 11 PASSED: measured results saved. Next: PUBLISH.ps1.')
        finally:
            if old_mode!='off':c.admin.command('balancerStart')
