import sys,unittest,tempfile,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import MagicMock
from collections import namedtuple
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from core import cache_hit,replica_details,alerts_for,retention,write_json
class MonitoringTests(unittest.TestCase):
    def test_hit_uses_deltas(self):
        self.assertAlmostEqual(cache_hit({'uptime':1,'pages_requested':100,'pages_read':50},{'uptime':31,'pages_requested':200,'pages_read':60}),90)
    def test_no_initial_fake_hit(self):self.assertIsNone(cache_hit(None,{}))
    def test_idle_not_zero_hit(self):self.assertIsNone(cache_hit({'uptime':1,'pages_requested':1,'pages_read':0},{'uptime':2,'pages_requested':1,'pages_read':0}))
    def test_restart_not_negative_hit(self):self.assertIsNone(cache_hit({'uptime':100,'pages_requested':1000,'pages_read':100},{'uptime':1,'pages_requested':10,'pages_read':1}))
    def test_unavailable_counters(self):self.assertIsNone(cache_hit({'uptime':1},{'uptime':2}))
    def test_replication_datetime_difference(self):
        now=datetime.now(timezone.utc)
        members,lags=replica_details({'members':[{'name':'p','stateStr':'PRIMARY','optimeDate':now},{'name':'s','stateStr':'SECONDARY','optimeDate':now-timedelta(seconds=12)}]})
        self.assertEqual(lags,{'s':12})
    def test_no_secondary_is_na(self):self.assertEqual(replica_details({'members':[]})[1],{})
    def test_threshold_boundaries(self):self.assertEqual(alerts_for({'cache_hit_percent':80,'replication_lag_seconds':{'s':10}}),[])
    def test_both_thresholds(self):self.assertEqual(len(alerts_for({'cache_hit_percent':79,'replication_lag_seconds':{'s':11}})),2)
class RetentionTests(unittest.TestCase):
    def test_cleanup_only_old_completed_owned_folders(self):
        now=datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for label,age,completed in [('old',8,True),('recent',1,True),('incomplete',9,False)]:
                stamp=now-timedelta(days=age);p=root/('backup-'+stamp.strftime('%Y%m%dT%H%M%S%fZ'));p.mkdir();setattr(self,label,p)
                write_json(p/'manifest.json',{'kind':'exercise14-backup','completed':completed,'completed_at':stamp.isoformat()})
            other=root/'other';other.mkdir();(root/'backup-incorrect').mkdir()
            retention(root,now)
            self.assertFalse(self.old.exists());self.assertTrue(self.recent.exists());self.assertTrue(self.incomplete.exists());self.assertTrue(other.exists())
    def test_does_not_follow_symlink(self):
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            link=Path(a)/'backup-20000101T000000000000Z'
            link.symlink_to(b,target_is_directory=True);retention(a);self.assertTrue(Path(b).exists())