import sys,unittest,tempfile,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import MagicMock
from collections import namedtuple
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from hybrid import CircuitBreaker,BackendUnavailable,FraudQueryService
class CircuitTests(unittest.TestCase):
    def test_three_failures_then_skip_and_retry_after_30s(self):
        clock=[0.0];breaker=CircuitBreaker(clock=lambda:clock[0]);call=MagicMock(side_effect=OSError('offline'))
        for _ in range(3):
            with self.assertRaises(BackendUnavailable):breaker.call(call)
        with self.assertRaises(BackendUnavailable):breaker.call(call)
        self.assertEqual(call.call_count,3);clock[0]=29
        with self.assertRaises(BackendUnavailable):breaker.call(call)
        clock[0]=30;call.side_effect=None;call.return_value='recovered'
        self.assertEqual(breaker.call(call),'recovered');self.assertEqual(breaker.failures,0)
    def test_success_resets_consecutive_errors(self):
        b=CircuitBreaker()
        for _ in range(2):
            with self.assertRaises(BackendUnavailable):b.call(lambda:1/0)
        b.call(lambda:1);self.assertEqual(b.failures,0)
    def test_recovery_failure_reopens(self):
        clock=[0];b=CircuitBreaker(threshold=1,clock=lambda:clock[0])
        with self.assertRaises(BackendUnavailable):b.call(lambda:1/0)
        clock[0]=30
        with self.assertRaises(BackendUnavailable):b.call(lambda:1/0)
        self.assertEqual(b.opened_at,30)
class HybridTests(unittest.TestCase):
    def service(self):
        db=MagicMock();s=MagicMock();g=MagicMock()
        db.transactions.find_one.return_value={'txn_id':'T1','amount':5}
        Row=namedtuple('Row','user_id txn_id');s.execute.return_value=[Row('U1','T1')]
        g.session.return_value.__enter__.return_value.run.return_value.data.return_value=[]
        return FraudQueryService(db,s,g),db,s,g
    def test_routes_to_three_drivers(self):
        service,db,s,g=self.service();r=service.analyze('T1','U1')
        self.assertTrue(r['complete']);db.transactions.find_one.assert_called_once_with({'txn_id':'T1'},{'_id':0});s.execute.assert_called_once();g.session.assert_called_once()
    def test_failed_backend_keeps_other_results(self):
        service,db,s,g=self.service();s.execute.side_effect=OSError('unavailable');r=service.analyze('T1','U1')
        self.assertFalse(r['complete']);self.assertEqual(r['backends']['cassandra']['status'],'unavailable');self.assertEqual(r['backends']['mongodb']['status'],'ok');self.assertEqual(r['backends']['neo4j']['status'],'ok')
    def test_hops_rejects_injection_and_extreme_values(self):
        service,*_=self.service()
        for hops in ('3 DELETE n',0,6,True):
            with self.assertRaises(ValueError):service.detect_fraud_rings('U1',hops)