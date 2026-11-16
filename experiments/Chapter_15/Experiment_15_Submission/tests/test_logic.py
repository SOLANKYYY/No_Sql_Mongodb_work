import sys,unittest,tempfile,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import MagicMock
from collections import namedtuple
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
class ApiPolicyTests(unittest.TestCase):
    def test_regular_scope_has_tenant_and_owner(self):
        from api import scoped
        self.assertEqual(scoped({'tenant_id':'a','_id':'alice','role':'user'}),{'tenant_id':'a','owner_id':'alice'})
    def test_admin_still_scoped_to_tenant(self):
        from api import scoped
        self.assertEqual(scoped({'tenant_id':'a','_id':'admin','role':'admin'}),{'tenant_id':'a'})
    def test_body_cannot_change_identity(self):
        from api import TaskCreate,TaskUpdate
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):TaskCreate(title='x',tenant_id='b')
        with self.assertRaises(ValidationError):TaskUpdate(owner_id='other')
    def test_password_hash_not_plaintext_and_verifies(self):
        from api import password_hash,check_password
        value=password_hash('example');self.assertNotIn('example',value);self.assertTrue(check_password('example',value));self.assertFalse(check_password('wrong',value))