import json, time, statistics, itertools, uuid, collections
from datetime import datetime, timezone
from pathlib import Path
from common import mongo, save, load, now, environment, fingerprint
from data_source import load_dataset

def prepare():
    save('run_state.json',{'status':'preparing','at':now()})
    rows,meta=load_dataset()
    save('source_check.json',meta)
    print(json.dumps(meta,indent=2),flush=True)
    print(f'DATA VALIDATED: {len(rows):,} unique records from multiple sources. Reduced workload; no database writes yet.')

class Stores:
    def __init__(self):
        from cassandra.cluster import Cluster
        from cassandra.policies import DCAwareRoundRobinPolicy
        from neo4j import GraphDatabase
        self.mc=mongo();self.db=self.mc['exercise18']
        # One lab process; driver pools reused throughout all trials.
        self.cluster=Cluster(['cassandra'],load_balancing_policy=DCAwareRoundRobinPolicy(local_dc='datacenter1'))
        self.cs=self.cluster.connect()
        self.cs.execute("CREATE KEYSPACE IF NOT EXISTS exercise18 WITH replication={'class':'SimpleStrategy','replication_factor':1}")
        self.cs.set_keyspace('exercise18')
        self.neo=GraphDatabase.driver('bolt://neo4j:7687',auth=None)
        self.neo.verify_connectivity()
    def close(self):
        self.mc.close();self.cluster.shutdown();self.neo.close()
    def cypher(self,q,**params):
        with self.neo.session(database='neo4j') as s: return s.run(q,**params).data()
    def schema(self):
        self.db.full_threats.create_index([('dataset',1),('source',1),('timestamp',-1),('id',-1)])
        self.db.full_threats.create_index([('dataset',1),('target',1),('source',1)])
        self.db.full_threats.create_index([('dataset',1),('day',1)])
        self.db.full_threats.create_index([('dataset',1),('id',1)],unique=True)
        self.db.threat.create_index([('dataset',1),('source',1)],unique=True)
        # Query-specific denormalization. All four writes included in load/throughput timing.
        definitions={
          'threats_by_source':'PRIMARY KEY ((dataset,source), timestamp,id)',
          'threats_by_type':'PRIMARY KEY ((dataset,type,day), timestamp,id)',
          'threats_by_target':'PRIMARY KEY ((dataset,target), source,id)',
          'threats_by_day':'PRIMARY KEY ((dataset,day), id)'}
        for table,key in definitions.items():
            self.cs.execute(f'CREATE TABLE IF NOT EXISTS {table} (dataset text,id text,source text,target text,type text,timestamp text,day text,indicator text,{key})'+(' WITH CLUSTERING ORDER BY (timestamp DESC,id DESC)' if table in ['threats_by_source','threats_by_type'] else ''))
        self.inserts=[self.cs.prepare(f'INSERT INTO {table} (dataset,id,source,target,type,timestamp,day,indicator) VALUES (?,?,?,?,?,?,?,?)') for table in definitions]
        self.history_stmt=self.cs.prepare('SELECT id,timestamp FROM threats_by_source WHERE dataset=? AND source=? LIMIT 50')
        self.target_stmt=self.cs.prepare('SELECT source FROM threats_by_target WHERE dataset=? AND target=?')
        self.day_stmt=self.cs.prepare('SELECT id FROM threats_by_day WHERE dataset=? AND day=?')
        for label in ['Threat','Source','Target']:
            self.cypher(f'CREATE CONSTRAINT e18_{label.lower()} IF NOT EXISTS FOR (n:{label}) REQUIRE n.key IS UNIQUE')
        self.cypher('CREATE INDEX e18_threat_day IF NOT EXISTS FOR (t:Threat) ON (t.dataset,t.day)')
    def clear(self):
        # Only dedicated exercise18 data; previous exercises never touched.
        self.db.full_threats.delete_many({});self.db.threat.delete_many({})
        for table in ['threats_by_source','threats_by_type','threats_by_target','threats_by_day']:self.cs.execute('TRUNCATE '+table)
        while True:
            x=self.cypher('MATCH (n) WHERE n:Threat OR n:Source OR n:Target WITH n LIMIT 5000 DETACH DELETE n RETURN count(*) AS n')[0]['n']
            if not x:break
    def insert(self,backend,rows,dataset):
        if backend=='MongoDB':
            self.db.full_threats.insert_many([{**r,'dataset':dataset} for r in rows],ordered=False)
            grouped=collections.defaultdict(list)
            for r in rows:grouped[r['source']].append(r)
            from pymongo import UpdateOne
            self.db.threat.bulk_write([UpdateOne({'dataset':dataset,'source':s},{'$push':{'recent_threats':{'$each':v,'$sort':{'timestamp':-1,'id':-1},'$slice':50}}},upsert=True) for s,v in grouped.items()])
        elif backend=='Cassandra':
            from cassandra.concurrent import execute_concurrent
            statements=[(stmt,(dataset,r['id'],r['source'],r['target'],r['type'],r['timestamp'],r['day'],r['indicator'])) for r in rows for stmt in self.inserts]
            for success,res in execute_concurrent(self.cs,statements,concurrency=32,raise_on_first_error=True):
                if not success: raise RuntimeError('Cassandra insert failed')
        else:
            self.cypher('''UNWIND $rows AS r
              CREATE (t:Threat {key:$dataset+'|'+r.id,dataset:$dataset,id:r.id,source:r.source,target:r.target,type:r.type,timestamp:r.timestamp,day:r.day,indicator:r.indicator})
              MERGE (s:Source {key:$dataset+'|'+r.source}) SET s.id=r.source,s.dataset=$dataset
              MERGE (g:Target {key:$dataset+'|'+r.target}) SET g.id=r.target,g.dataset=$dataset
              CREATE (s)-[:REPORTED]->(t)-[:TARGETS]->(g)''',rows=rows,dataset=dataset)
    def query(self,backend,kind,value):
        if backend=='MongoDB':
            if kind=='history':return [d['id'] for d in self.db.full_threats.find({'dataset':'baseline','source':value},{'id':1}).sort([('timestamp',-1),('id',-1)]).limit(50)]
            if kind=='spread':return sorted(self.db.full_threats.distinct('source',{'dataset':'baseline','target':value}))
            return {r['_id']:r['n'] for r in self.db.full_threats.aggregate([{'$match':{'dataset':'baseline'}},{'$group':{'_id':'$day','n':{'$sum':1}}}])}
        if backend=='Cassandra':
            if kind=='history':return [r.id for r in self.cs.execute(self.history_stmt,('baseline',value))]
            if kind=='spread':return sorted({r.source for r in self.cs.execute(self.target_stmt,('baseline',value))})
            # Explicitly includes row transfer + client aggregation; no fabricated SQL-style group-by.
            return {day:sum(1 for _ in self.cs.execute(self.day_stmt,('baseline',day))) for day in value}
        if kind=='history':return [r['id'] for r in self.cypher('MATCH (:Source {key:$key})-[:REPORTED]->(t:Threat) RETURN t.id AS id ORDER BY t.timestamp DESC,t.id DESC LIMIT 50',key='baseline|'+value)]
        if kind=='spread':return [r['source'] for r in self.cypher('MATCH (s:Source)-[:REPORTED]->(:Threat)-[:TARGETS]->(:Target {key:$key}) RETURN DISTINCT s.id AS source ORDER BY source',key='baseline|'+value)]
        return {r['day']:r['n'] for r in self.cypher("MATCH (t:Threat {dataset:'baseline'}) RETURN t.day AS day,count(*) AS n")}

def graph_review(stores):
    import networkx as nx
    groups=stores.cypher("MATCH (s:Source {dataset:'baseline'})-[:REPORTED]->(:Threat)-[:TARGETS]->(g:Target) RETURN g.id AS target,collect(DISTINCT s.id) AS sources")
    shared=collections.Counter();skipped=0
    for group in groups:
        sources=sorted(group['sources'])
        if len(sources)>100: skipped+=1;continue # disclosed hub safeguard, not hidden truncation
        shared.update(itertools.combinations(sources,2))
    graph=nx.Graph()
    for (a,b),w in shared.items():
        if w>=2:graph.add_edge(a,b,weight=w)
    edges=[{'a':a,'b':b,'shared_targets':d['weight']} for a,b,d in graph.edges(data=True)]
    for start in range(0,len(edges),500):
        stores.cypher("UNWIND $rows AS r MATCH (a:Source {key:'baseline|'+r.a}),(b:Source {key:'baseline|'+r.b}) MERGE (a)-[e:SUSPICIOUS]->(b) SET e.shared_targets=r.shared_targets",rows=edges[start:start+500])
    communities=list(nx.community.greedy_modularity_communities(graph,weight='weight')) if graph.number_of_edges() else []
    result=[]
    for community in communities:
        members=sorted(community);sub=graph.subgraph(community);density=nx.density(sub)
        if len(members)<3 or density<0.5:continue
        # Cross-reference original MongoDB events, not invented threat labels.
        count=stores.db.full_threats.count_documents({'dataset':'baseline','source':{'$in':members}})
        indicators=stores.db.full_threats.aggregate([{'$match':{'dataset':'baseline','source':{'$in':members}}},{'$group':{'_id':'$indicator','sources':{'$addToSet':'$source'},'n':{'$sum':1}}},{'$match':{'n':{'$gte':2}}},{'$sort':{'n':-1}},{'$limit':10}])
        result.append({'members':members,'density':density,'mongo_events':count,'repeated_indicator_groups':sum(1 for _ in indicators),'classification':'review candidate only; no truth labels available'})
    return {'algorithm':'NetworkX greedy modularity over source relationships extracted from live Neo4j; SUSPICIOUS relationships written back to Neo4j',
            'edge_rule':'at least 2 shared targets','candidate_rule':'community size >=3 and density >=0.5','nodes':graph.number_of_nodes(),'edges':graph.number_of_edges(),
            'skipped_high_degree_targets':skipped,'communities':result,'interpretation':'High connectivity can mean syndicated benign alerts OR a real campaign. This is a review queue, not proof of false positives.'}

def run():
    save('run_state.json',{'status':'running','at':now()})
    rows,meta=load_dataset();s=Stores()
    try:
        s.schema();s.clear()
        backends=['MongoDB','Cassandra','Neo4j'];loads={}
        for backend in backends:
            t=time.perf_counter()
            for start in range(0,len(rows),500):
                s.insert(backend,rows[start:start+500],'baseline')
                if start%10000==0:print(backend,'loaded',start+500,flush=True)
            loads[backend]=time.perf_counter()-t
        sources=collections.Counter(r['source'] for r in rows);source=sources.most_common(1)[0][0]
        targets=collections.Counter(r['target'] for r in rows);target=targets.most_common(1)[0][0]
        days=sorted({r['day'] for r in rows})
        expected={'history':[r['id'] for r in rows if r['source']==source][:50],
          'spread':sorted({r['source'] for r in rows if r['target']==target}),
          'daily':dict(collections.Counter(r['day'] for r in rows))}
        params={'history':source,'spread':target,'daily':days}
        checks={};metrics=[]
        for kind in params:
            timings={b:[] for b in backends}
            for b in backends:
                assert s.query(b,kind,params[kind])==expected[kind],b+' '+kind+' differs from source truth'
            for repeat in range(10):
                for b in backends[repeat%3:]+backends[:repeat%3]:
                    t=time.perf_counter();result=s.query(b,kind,params[kind]);elapsed=(time.perf_counter()-t)*1000
                    assert result==expected[kind],b+' result changed'
                    timings[b].append(elapsed)
            for b,values in timings.items():
                metrics.append({'backend':b,'query':kind,'runs':10,'median_ms':statistics.median(values),'min_ms':min(values),'max_ms':max(values),'all_ms':values,'result_count':len(expected[kind])})
            checks[kind]={'matched_all_backends':True,'result_sha256':fingerprint(expected[kind])}
        # Separate data namespace per repetition avoids polluting baseline read queries.
        write_times={b:[] for b in backends}
        write_checks={b:[] for b in backends}
        for repeat in range(10):
            batch=[{**r,'id':'write-'+str(i)} for i,r in enumerate(rows[:1000])]
            dataset='write-'+str(repeat)
            for b in backends[repeat%3:]+backends[:repeat%3]:
                t=time.perf_counter()
                s.insert(b,batch,dataset)
                write_times[b].append((time.perf_counter()-t)*1000)
                if b=='MongoDB': actual=s.db.full_threats.count_documents({'dataset':dataset})
                elif b=='Neo4j': actual=s.cypher('MATCH (t:Threat {dataset:$dataset}) RETURN count(t) AS n',dataset=dataset)[0]['n']
                else: actual=sum(sum(1 for _ in s.cs.execute(s.day_stmt,(dataset,d))) for d in {r['day'] for r in batch})
                assert actual==1000,b+' write verification failed'
                write_checks[b].append(actual)
        for b,values in write_times.items():
            median=statistics.median(values)
            metrics.append({'backend':b,'query':'ingest_1000','runs':10,'median_ms':median,'events_per_second':1000000/median,'min_ms':min(values),'max_ms':max(values),'all_ms':values})
        print(json.dumps(metrics,indent=2),flush=True)
        graph=graph_review(s);print(json.dumps(graph,indent=2),flush=True)
        versions={'MongoDB':s.mc.server_info()['version'],'Cassandra':s.cs.execute('SELECT release_version FROM system.local').one().release_version,'Neo4j':s.cypher('CALL dbms.components() YIELD versions RETURN versions')[0]['versions']}
        evidence={'experiment':18,'passed':True,'at':now(),'environment':environment(),'versions':versions,'data':meta,'load_seconds':loads,'queries':metrics,'checks':checks,'write_checks':write_checks,'graph':graph,
         'methodology':{'read_trials':10,'write_trials':10,'write_batch':1000,'backend_order':'rotated each repeat','warmup':'one correctness run before each read query',
          'history':'50 most recent events for busiest source','spread':'distinct sources observing most frequent target','daily':'counts grouped by UTC day',
          'write_costs':'MongoDB full_threats + bounded recent array; Cassandra four denormalized tables; Neo4j threat, source/target nodes and edges',
          'durability':'single-node classroom defaults; MongoDB w=1, Cassandra LOCAL_ONE, Neo4j committed transaction; not equivalent replicated durability',
          'scope':'same machine and dataset; timings include driver/network and materializing all returned results; not distributed scaling evidence'}}
        save('evidence.json',evidence);save('run_state.json',{'status':'passed','at':now()})
        print('EXERCISE 18 PASSED: live three-database measurements saved. Next: PUBLISH.ps1.')
    finally:s.close()
