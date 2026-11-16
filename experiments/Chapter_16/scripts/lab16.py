"""Live, equivalent university queries and a three-engine fraud investigation."""
import statistics,uuid
from datetime import datetime,timezone,timedelta
from core import save,utc
from hybrid import connect_backends,FraudQueryService

STUDENTS={'S1':'Alice','S2':'Bob','S3':'Carol','S4':'Dev'}
COURSES={'C1':'Databases','C2':'Machine Learning','C3':'Distributed Systems'}
ENROLMENTS=[('S1','C1'),('S1','C2'),('S2','C1'),('S3','C2'),('S3','C3'),('S4','C3')]

def cql_setup(s):
    s.execute("CREATE KEYSPACE IF NOT EXISTS exercise16 WITH replication = {'class':'SimpleStrategy','replication_factor':1}")
    statements=[
      'CREATE TABLE IF NOT EXISTS exercise16.student_courses (student_id text,course_id text,course_title text,PRIMARY KEY ((student_id),course_id))',
      'CREATE TABLE IF NOT EXISTS exercise16.course_students (course_id text,student_id text,student_name text,PRIMARY KEY ((course_id),student_id))',
      'CREATE TABLE IF NOT EXISTS exercise16.audit_by_student (student_id text,event_time timestamp,event_id uuid,action text,course_id text,PRIMARY KEY ((student_id),event_time,event_id)) WITH CLUSTERING ORDER BY (event_time DESC,event_id ASC)',
      'CREATE TABLE IF NOT EXISTS exercise16.user_profiles (user_id text,event_time timestamp,event_id text,txn_id text,amount double,merchant text,PRIMARY KEY ((user_id),event_time,event_id)) WITH CLUSTERING ORDER BY (event_time DESC,event_id ASC)']
    for q in statements:s.execute(q)
    for table in ['student_courses','course_students','audit_by_student','user_profiles']:s.execute('TRUNCATE exercise16.'+table)

def timed(fn,n=20):
    fn();samples=[]
    for _ in range(n):
        import time
        start=time.perf_counter();fn();samples.append((time.perf_counter()-start)*1000)
    return {'samples':n,'median_ms':statistics.median(samples),'mean_ms':statistics.mean(samples),'min_ms':min(samples),'max_ms':max(samples)}

def university(mongo,s,graph):
    db=mongo.exercise16
    for name in ['students','courses']:db[name].drop()
    db.students.insert_many([{'_id':sid,'name':name,'course_ids':[cid for a,cid in ENROLMENTS if a==sid]} for sid,name in STUDENTS.items()])
    db.courses.insert_many([{'_id':cid,'title':name,'student_roster':[{'student_id':sid,'name':STUDENTS[sid]} for sid,c in ENROLMENTS if c==cid]} for cid,name in COURSES.items()])
    db.students.create_index('course_ids')
    ins_sc=s.prepare('INSERT INTO exercise16.student_courses (student_id,course_id,course_title) VALUES (?,?,?)')
    ins_cs=s.prepare('INSERT INTO exercise16.course_students (course_id,student_id,student_name) VALUES (?,?,?)')
    ins_audit=s.prepare('INSERT INTO exercise16.audit_by_student (student_id,event_time,event_id,action,course_id) VALUES (?,?,?,?,?)')
    now=datetime.now(timezone.utc)
    for sid,cid in ENROLMENTS:
        s.execute(ins_sc,[sid,cid,COURSES[cid]]);s.execute(ins_cs,[cid,sid,STUDENTS[sid]])
        s.execute(ins_audit,[sid,now,uuid.uuid4(),'ENROLLED',cid])
    with graph.session() as g:
        g.run('MATCH (n) WHERE n:E16Student OR n:E16Course DETACH DELETE n').consume()
        for label in ['E16Student','E16Course']:g.run(f'CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE').consume()
        for sid,name in STUDENTS.items():g.run('CREATE (:E16Student {id:$id,name:$name})',id=sid,name=name).consume()
        for cid,name in COURSES.items():g.run('CREATE (:E16Course {id:$id,title:$title})',id=cid,title=name).consume()
        for sid,cid in ENROLMENTS:g.run('MATCH (s:E16Student {id:$sid}),(c:E16Course {id:$cid}) CREATE (s)-[:ENROLLED_IN]->(c)',sid=sid,cid=cid).consume()
        for a,b in [('C3','C2'),('C2','C1')]:g.run('MATCH (a:E16Course {id:$a}),(b:E16Course {id:$b}) CREATE (a)-[:REQUIRES]->(b)',a=a,b=b).consume()
    qsc=s.prepare('SELECT course_id FROM exercise16.student_courses WHERE student_id=?')
    qcs=s.prepare('SELECT student_id FROM exercise16.course_students WHERE course_id=?')
    def mongo_queries():
        course_ids=db.students.find_one({'_id':'S1'})['course_ids']
        return {'courses_for_S1':sorted(course_ids),'students_in_C1':sorted(x['student_id'] for x in db.courses.find_one({'_id':'C1'})['student_roster']),
                'shared_course_peers_of_S1':sorted(x['_id'] for x in db.students.find({'_id':{'$ne':'S1'},'course_ids':{'$in':course_ids}}))}
    def cassandra_queries():
        ids=sorted(x.course_id for x in s.execute(qsc,['S1']));peers=set()
        for cid in ids:peers.update(x.student_id for x in s.execute(qcs,[cid]))
        return {'courses_for_S1':ids,'students_in_C1':sorted(x.student_id for x in s.execute(qcs,['C1'])),'shared_course_peers_of_S1':sorted(peers-{'S1'})}
    def neo_queries():
        with graph.session() as g:
            courses=g.run('MATCH (:E16Student {id:$sid})-[:ENROLLED_IN]->(c:E16Course) RETURN c.id AS id ORDER BY id',sid='S1').data()
            students=g.run('MATCH (s:E16Student)-[:ENROLLED_IN]->(:E16Course {id:$cid}) RETURN s.id AS id ORDER BY id',cid='C1').data()
            peers=g.run('MATCH (a:E16Student {id:$sid})-[:ENROLLED_IN]->(:E16Course)<-[:ENROLLED_IN]-(b:E16Student) WHERE a<>b RETURN DISTINCT b.id AS id ORDER BY id',sid='S1').data()
        return dict(zip(['courses_for_S1','students_in_C1','shared_course_peers_of_S1'],[[r['id'] for r in x] for x in [courses,students,peers]]))
    expected={'courses_for_S1':['C1','C2'],'students_in_C1':['S1','S2'],'shared_course_peers_of_S1':['S2','S3']}
    outputs={name:fn() for name,fn in [('mongodb',mongo_queries),('cassandra',cassandra_queries),('neo4j',neo_queries)]}
    with graph.session() as g:prereqs=[x['id'] for x in g.run('MATCH (:E16Course {id:$cid})-[:REQUIRES*1..5]->(p:E16Course) RETURN DISTINCT p.id AS id ORDER BY id',cid='C3')]
    audit=list(s.execute(s.prepare('SELECT * FROM exercise16.audit_by_student WHERE student_id=?'),['S1']))
    result={'timestamp':utc(),'live_backends':['MongoDB','Cassandra','Neo4j'],'expected':expected,'observed':outputs,
            'hybrid_enrollment_activity':{'operational_student':db.students.find_one({'_id':'S1'}),'audit_event_count':len(audit),'prerequisites_for_C3':prereqs},
            'timings':{name:timed(fn) for name,fn in [('mongodb',mongo_queries),('cassandra',cassandra_queries),('neo4j',neo_queries)]},
            'passed':all(x==expected for x in outputs.values()) and len(audit)==2 and prereqs==['C1','C2']}
    save('lab16_1_models.json',result)
    if not result['passed']:raise RuntimeError('Equivalent-query or hybrid architecture check failed.')

def fraud(mongo,s,graph):
    db=mongo.exercise16;db.transactions.drop();now=datetime.now(timezone.utc)
    transactions=[{'txn_id':'TX-001','user_id':'U1','amount':50000.0,'merchant':'Example Store','timestamp':now,'risk_score':0.92},
                  {'txn_id':'TX-002','user_id':'U1','amount':250.0,'merchant':'Books','timestamp':now-timedelta(hours=1),'risk_score':0.12},
                  {'txn_id':'TX-003','user_id':'U2','amount':12000.0,'merchant':'Transfer','timestamp':now-timedelta(minutes=5),'risk_score':0.7}]
    db.transactions.insert_many(transactions);db.transactions.create_index('txn_id',unique=True)
    insert=s.prepare('INSERT INTO exercise16.user_profiles (user_id,event_time,event_id,txn_id,amount,merchant) VALUES (?,?,?,?,?,?)')
    for tx in transactions:s.execute(insert,[tx['user_id'],tx['timestamp'],tx['txn_id'],tx['txn_id'],tx['amount'],tx['merchant']])
    with graph.session() as g:
        g.run('MATCH (u:E16User) DETACH DELETE u').consume()
        g.run('CREATE CONSTRAINT e16user_id IF NOT EXISTS FOR (u:E16User) REQUIRE u.id IS UNIQUE').consume()
        for uid in ['U1','U2','U3','U4','U5']:g.run('CREATE (:E16User {id:$id})',id=uid).consume()
        for a,b in [('U1','U2'),('U2','U3'),('U3','U1'),('U3','U4')]:g.run('MATCH (a:E16User {id:$a}),(b:E16User {id:$b}) CREATE (a)-[:TRANSFERRED_TO]->(b)',a=a,b=b).consume()
    service=FraudQueryService(db,s,graph);analysis=service.analyze('TX-001','U1',3)
    profile=analysis['backends']['cassandra'].get('data',[]);network=analysis['backends']['neo4j'].get('data',{})
    checks={'all_live_backends_succeeded':analysis['complete'],'transaction_lookup':analysis['backends']['mongodb'].get('data',{}).get('amount')==50000,
            'time_ordered_profile':[x['txn_id'] for x in profile]==['TX-001','TX-002'],
            'connected_accounts':{x['id'] for x in network.get('connected_accounts',[])}=={'U2','U3','U4'},
            'directed_cycle_found':any(set(x)=={'U1','U2','U3'} for x in network.get('directed_cycles',[]))}
    timings={'transaction':timed(lambda:service.get_transaction('TX-001')),'profile':timed(lambda:service.get_user_profile('U1'))}
    for hops in (1,2,3):timings[f'graph_{hops}_hops']=timed(lambda h=hops:service.detect_fraud_rings('U1',h))
    save('lab16_2_hybrid.json',{'timestamp':utc(),'passed':all(checks.values()),'checks':checks,'analysis':analysis,'latencies':timings,
                              'performance_scope':'20 warm repetitions on a tiny local dataset; observations are not production latency guarantees.'})
    if not all(checks.values()):raise RuntimeError('Live fraud workflow validation failed.')

def run():
    mongo,cluster,s,graph=connect_backends()
    try:cql_setup(s);university(mongo,s,graph);fraud(mongo,s,graph)
    finally:graph.close();cluster.shutdown();mongo.close()
