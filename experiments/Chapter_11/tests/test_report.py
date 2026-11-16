import unittest
from unittest.mock import patch
import report
from common import EXPERIMENT
class ReportTests(unittest.TestCase):
 def test_digest_array_rejected(self):
  repo='solankyyy/nosql-exercise'+str(EXPERIMENT)
  p={'image':repo+':exercise'+str(EXPERIMENT),'docker_url':'https://hub.docker.com/r/'+repo,'digest':[repo+'@sha256:'+'a'*64],'verified_pull':True}
  with patch.object(report,'load',return_value=p):
   with self.assertRaises(ValueError):report.publication()
 def test_missing_evidence_cannot_validate(self):
  with patch.object(report,'load',return_value={}):
   with self.assertRaises(ValueError):report.validate()
 def test_failed_latest_run_blocks_old_pass(self):
  with patch.object(report,'load',side_effect=[{'experiment':EXPERIMENT,'passed':True},{'status':'failed'}]):
   with self.assertRaises(ValueError):report.validate()
 def test_url_and_digest_must_match_repository(self):
  repo='solankyyy/nosql-exercise'+str(EXPERIMENT)
  p={'image':repo+':exercise'+str(EXPERIMENT),'docker_url':'https://hub.docker.com/r/'+repo,'digest':repo+'@sha256:'+'a'*64,'verified_pull':True}
  with patch.object(report,'load',return_value=p):self.assertEqual(report.publication(),p)
  p['docker_url']='https://hub.docker.com/r/other/repository'
  with patch.object(report,'load',return_value=p):
   with self.assertRaises(ValueError):report.publication()
