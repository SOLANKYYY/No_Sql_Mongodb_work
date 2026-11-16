"""Lab 16.2: pooled drivers, one breaker per backend, explicit partial results."""
import time,threading
class BackendUnavailable(RuntimeError):pass

class CircuitBreaker:
    def __init__(self,threshold=3,cooldown=30,clock=time.monotonic):
        self.threshold=threshold;self.cooldown=cooldown;self.clock=clock;self.failures=0;self.opened_at=None;self.probing=False;self.lock=threading.Lock()
    def call(self,fn):
        with self.lock:
            if self.opened_at is not None:
                if self.clock()-self.opened_at<self.cooldown or self.probing:raise BackendUnavailable('Circuit open; backend call skipped')
                self.probing=True
        try:value=fn()
        except Exception as exc:
            with self.lock:
                self.failures+=1
                if self.failures>=self.threshold:self.opened_at=self.clock()
                self.probing=False
            raise BackendUnavailable(type(exc).__name__) from exc
        with self.lock:self.failures=0;self.opened_at=None;self.probing=False
        return value

def connect_backends():
    from core import client
    from cassandra.cluster import Cluster
    from cassandra.policies import DCAwareRoundRobinPolicy
    from neo4j import GraphDatabase
    mongo=client()
    # One sequential lab service; driver sessions are reused, never opened per request.
    # Four executor threads handle Cassandra metadata/control work, not four connections.
    cluster=Cluster(['cassandra'],executor_threads=4,load_balancing_policy=DCAwareRoundRobinPolicy(local_dc='datacenter1'))
    session=None;graph=None
    try:
        mongo.admin.command('ping');session=cluster.connect();session.default_timeout=30
        # Tiny local graph and at most a few concurrent demos: ten pooled connections suffice.
        graph=GraphDatabase.driver('bolt://neo4j:7687',auth=None,max_connection_pool_size=10,connection_timeout=10)
        graph.verify_connectivity();return mongo,cluster,session,graph
    except Exception:
        mongo.close();cluster.shutdown()
        if graph:graph.close()
        raise

class FraudQueryService:
    def __init__(self,mongo_db,cassandra_session,neo4j_driver,clock=time.monotonic):
        self.mongo=mongo_db;self.cassandra=cassandra_session;self.graph=neo4j_driver
        self.profile_query=self.cassandra.prepare('SELECT user_id,event_time,event_id,txn_id,amount,merchant FROM exercise16.user_profiles WHERE user_id=? LIMIT 10')
        self.breakers={name:CircuitBreaker(clock=clock) for name in ('mongodb','cassandra','neo4j')}
    def get_transaction(self,txn_id):
        return self.breakers['mongodb'].call(lambda:self.mongo.transactions.find_one({'txn_id':txn_id},{'_id':0}))
    def get_user_profile(self,user_id):
        def query():return [dict(x._asdict()) for x in self.cassandra.execute(self.profile_query,[user_id])]
        return self.breakers['cassandra'].call(query)
    def detect_fraud_rings(self,user_id,max_hops=3):
        if isinstance(max_hops,bool) or not isinstance(max_hops,int) or not 1<=max_hops<=5:raise ValueError('max_hops must be an integer from 1 to 5')
        def query():
            with self.graph.session() as session:
                connected=session.run(f'MATCH p=(a:E16User {{id:$uid}})-[:TRANSFERRED_TO*1..{max_hops}]-(b:E16User) WHERE b <> a RETURN b.id AS id,min(length(p)) AS hops ORDER BY hops,id LIMIT 50',uid=user_id).data()
                cycles=session.run(f'MATCH p=(a:E16User {{id:$uid}})-[:TRANSFERRED_TO*2..{max_hops}]->(a) RETURN DISTINCT [n IN nodes(p) | n.id] AS cycle LIMIT 20',uid=user_id).data()
            return {'connected_accounts':connected,'directed_cycles':[x['cycle'] for x in cycles],'interpretation':'Connectivity and cycles are investigation signals, not proof of fraud.'}
        return self.breakers['neo4j'].call(query)
    def analyze(self,txn_id,user_id,max_hops=3):
        result={'transaction_id':txn_id,'user_id':user_id,'backends':{}}
        methods={'mongodb':lambda:self.get_transaction(txn_id),'cassandra':lambda:self.get_user_profile(user_id),'neo4j':lambda:self.detect_fraud_rings(user_id,max_hops)}
        for name,fn in methods.items():
            started=time.perf_counter()
            try:result['backends'][name]={'status':'ok','data':fn(),'milliseconds':(time.perf_counter()-started)*1000}
            except BackendUnavailable as e:result['backends'][name]={'status':'unavailable','error':str(e),'milliseconds':(time.perf_counter()-started)*1000}
        result['complete']=all(x['status']=='ok' for x in result['backends'].values());return result
