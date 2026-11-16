"""Generate a lab CA and hostname-validated server/client certificates; never bake keys into images."""
import os,ipaddress,json,secrets
from pathlib import Path
from datetime import datetime,timedelta,timezone
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID

def private(key):return key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
def make_ca(name):
 key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
 subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,name)])
 n=datetime.now(timezone.utc)
 cert=(x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
  .not_valid_before(n-timedelta(minutes=5)).not_valid_after(n+timedelta(days=365))
  .add_extension(x509.BasicConstraints(ca=True,path_length=0),True)
  .add_extension(x509.KeyUsage(False,False,False,False,False,True,True,False,False),True).sign(key,hashes.SHA256()))
 return key,cert

def make_leaf(ca_key,ca,server):
 key=rsa.generate_private_key(public_exponent=65537,key_size=3072);n=datetime.now(timezone.utc)
 subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'mongo' if server else 'exercise12-client')])
 builder=(x509.CertificateBuilder().subject_name(subject).issuer_name(ca.subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
  .not_valid_before(n-timedelta(minutes=5)).not_valid_after(n+timedelta(days=180))
  .add_extension(x509.BasicConstraints(ca=False,path_length=None),True)
  .add_extension(x509.KeyUsage(True,False,True,False,False,False,False,False,False),True)
  .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH if server else ExtendedKeyUsageOID.CLIENT_AUTH]),False))
 if server:builder=builder.add_extension(x509.SubjectAlternativeName([x509.DNSName('mongo'),x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),False)
 return key,builder.sign(ca_key,hashes.SHA256())

def prepare(secrets_dir,certs_dir):
 secrets_dir.mkdir(parents=True,exist_ok=True);certs_dir.mkdir(parents=True,exist_ok=True)
 credential_file=secrets_dir/'credentials.json'
 required=['ca.crt','ca.key','server.pem','server.crt','client.pem','client.crt','wrong-ca.crt']
 if credential_file.exists():
  if not all((certs_dir/x).exists() for x in required):raise ValueError('Credentials exist but TLS volume is incomplete. Restore the original TLS volume; do not regenerate passwords against an existing database.')
  values=json.loads(credential_file.read_text())
 else:
  if any((certs_dir/x).exists() for x in required):raise ValueError('Partial existing TLS material found. Preserve it and inspect setup before proceeding.')
  values={user:secrets.token_urlsafe(32) for user in ['lab_admin','app_reader','app_writer','hr_user']}
  ca_key,ca=make_ca('Exercise12-Lab-CA');_,wrong=make_ca('Untrusted-Test-CA')
  (certs_dir/'ca.key').write_bytes(private(ca_key));(certs_dir/'ca.key').chmod(0o600)
  (certs_dir/'ca.crt').write_bytes(ca.public_bytes(serialization.Encoding.PEM))
  (certs_dir/'wrong-ca.crt').write_bytes(wrong.public_bytes(serialization.Encoding.PEM))
  for server,name in [(True,'server'),(False,'client')]:
   key,cert=make_leaf(ca_key,ca,server);pem=certs_dir/(name+'.pem')
   pem.write_bytes(private(key)+cert.public_bytes(serialization.Encoding.PEM));pem.chmod(0o600)
   (certs_dir/(name+'.crt')).write_bytes(cert.public_bytes(serialization.Encoding.PEM))
   if server and hasattr(os,'geteuid') and os.geteuid()==0:os.chown(pem,999,999)
  credential_file.write_text(json.dumps(values));credential_file.chmod(0o600)
 (secrets_dir/'root.env').write_text('MONGO_INITDB_ROOT_USERNAME=lab_admin\nMONGO_INITDB_ROOT_PASSWORD='+values['lab_admin']+'\n')
 print('Lab credentials and TLS material ready. Existing secrets reused; values not printed.')

def metadata(certs_dir):
 out={}
 for name in ('ca','server','client'):
  cert=x509.load_pem_x509_certificate((certs_dir/(name+'.crt')).read_bytes())
  out[name]={'subject':cert.subject.rfc4514_string(),'issuer':cert.issuer.rfc4514_string(),
   'sha256':cert.fingerprint(hashes.SHA256()).hex(),'not_after':cert.not_valid_after_utc.isoformat()}
 return out
