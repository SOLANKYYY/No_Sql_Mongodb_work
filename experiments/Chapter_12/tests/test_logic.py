import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from cryptography import x509
from cryptography.x509.oid import ExtendedKeyUsageOID
from certificates import make_ca,make_leaf
from lab import expect_denied
from pymongo.errors import OperationFailure
class Tests(unittest.TestCase):
 def test_real_chain_and_hostname_extension(self):
  k,ca=make_ca('test CA');_,server=make_leaf(k,ca,True)
  server.verify_directly_issued_by(ca)
  self.assertIn('mongo',server.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName))
  self.assertIn(ExtendedKeyUsageOID.SERVER_AUTH,server.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value)
 def test_unexpected_error_is_not_a_pass(self):
  def wrong():raise OperationFailure('network-like unrelated error',code=91)
  with self.assertRaises(OperationFailure):expect_denied(wrong)
 def test_success_is_not_a_denial(self):
  with self.assertRaises(AssertionError):expect_denied(lambda:1)
 def test_expected_code(self):
  def deny():raise OperationFailure('not authorized',code=13)
  self.assertEqual(expect_denied(deny)['error_code'],13)
if __name__=='__main__':unittest.main()
