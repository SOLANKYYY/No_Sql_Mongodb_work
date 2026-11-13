import json,os,socket,ssl
from pathlib import Path
from pymongo import MongoClient
from pymongo.errors import OperationFailure,ServerSelectionTimeoutError,ConnectionFailure
from common import save,now,environment
import certificates
SECRETS=Path(os.getenv('SECRETS_DIR','/secrets'));CERTS=Path(os.getenv('CERTS_DIR','/certs'))
HOST=os.getenv('MONGO_HOST','mongo');PORT=int(os.getenv('MONGO_PORT','27017'))

def prepare():certificates.prepare(SECRETS,CERTS)

def client(user=None,password=None,tls=True,ca=None):
 kwargs={'host':HOST,'port':PORT,'directConnection':True,
         # Negative transport tests must finish promptly; this is a local sequential lab.
         'serverSelectionTimeoutMS':4000,'connectTimeoutMS':3000}
 if tls:kwargs.update(tls=True,tlsCAFile=str(ca or CERTS/'ca.crt'),tlsCertificateKeyFile=str(CERTS/'client.pem'))
 if user:kwargs.update(username=user,password=password,authSource='admin')
 return MongoClient(**kwargs)

def role(admin,name,privileges):
 if admin.command('rolesInfo',{'role':name,'db':'admin'})['roles']:admin.command('updateRole',name,privileges=privileges,roles=[])
 else:admin.command('createRole',name,privileges=privileges,roles=[])

def user(admin,name,password,role_name):
 values={'pwd':password,'roles':[{'role':role_name,'db':'admin'}]}
 if admin.command('usersInfo',{'user':name,'db':'admin'})['users']:admin.command('updateUser',name,**values)
 else:admin.command('createUser',name,**values)

def expect_denied(operation,code=13):
 try:operation()
 except OperationFailure as e:
  if e.code!=code:raise
  return {'passed':True,'error_code':e.code,'outcome':'rejected as expected'}
 raise AssertionError('Operation unexpectedly succeeded')

def run():
 values=json.loads((SECRETS/'credentials.json').read_text())
 checks={}
 with client('lab_admin',values['lab_admin']) as admin:
  admin.admin.command('ping');parsed=admin.admin.command('getCmdLineOpts')['parsed']
  assert parsed.get('security',{}).get('authorization')=='enabled'
  assert parsed.get('net',{}).get('tls',{}).get('mode')=='requireTLS'
  d=admin.analytics
  # Synthetic lab-only collections; no external or prior coursework databases touched.
  d.orders.delete_many({});d.orders.insert_many([{'_id':i,'item':'Demo item','quantity':i+1} for i in range(10)])
  d.employees.replace_one({'_id':1},{'_id':1,'name':'Synthetic Employee A','department':'Engineering','salary':75000},upsert=True)
  d.employees.replace_one({'_id':2},{'_id':2,'name':'Synthetic Employee B','department':'HR','salary':82000},upsert=True)
  d.restricted.replace_one({'_id':1},{'_id':1,'note':'Restricted lab collection'},upsert=True)
  if 'employee_public' in d.list_collection_names():d.drop_collection('employee_public')
  d.command('create','employee_public',viewOn='employees',pipeline=[{'$project':{'salary':0}}])
  privilege=lambda coll,actions:{'resource':{'db':'analytics','collection':coll},'actions':actions}
  role(admin.admin,'ordersReader',[privilege('orders',['find']),privilege('employee_public',['find'])])
  role(admin.admin,'ordersWriter',[privilege('orders',['find','insert','update','remove'])])
  role(admin.admin,'hrReader',[privilege('employees',['find'])])
  for name,r in [('app_reader','ordersReader'),('app_writer','ordersWriter'),('hr_user','hrReader')]:user(admin.admin,name,values[name],r)
  checks['auth_enabled']={'passed':True};checks['tls_required']={'passed':True}
  version=admin.server_info()['version']
  with client('app_reader',values['app_reader']) as reader:
   assert reader.analytics.orders.find_one() is not None
   assert list(reader.analytics.orders.aggregate([{'$count':'n'}]))==[{'n':10}]
   checks['reader_find_and_aggregate']={'passed':True,'count':10}
   checks['reader_write_denied']=expect_denied(lambda:reader.analytics.orders.insert_one({'_id':999}))
   checks['reader_base_salary_denied']=expect_denied(lambda:reader.analytics.employees.find_one())
   checks['reader_other_collection_denied']=expect_denied(lambda:reader.analytics.restricted.find_one())
   public=list(reader.analytics.employee_public.find())
   assert len(public)==2 and all('salary' not in x for x in public)
   checks['salary_view_redacted']={'passed':True,'rows':public}
  with client('app_writer',values['app_writer']) as writer:
   writer.analytics.orders.insert_one({'_id':100,'item':'CRUD test','quantity':1})
   assert writer.analytics.orders.update_one({'_id':100},{'$set':{'quantity':2}}).modified_count==1
   assert writer.analytics.orders.find_one({'_id':100})['quantity']==2
   assert writer.analytics.orders.delete_one({'_id':100}).deleted_count==1
   checks['writer_scoped_crud']={'passed':True}
   checks['writer_other_collection_denied']=expect_denied(lambda:writer.analytics.restricted.insert_one({'_id':2}))
   checks['writer_salary_denied']=expect_denied(lambda:writer.analytics.employees.find_one())
  with client('hr_user',values['hr_user']) as hr:
   assert hr.analytics.employees.find_one({'_id':1})['salary']==75000
   checks['hr_salary_visible']={'passed':True,'synthetic_salary_value':75000}
   checks['hr_write_denied']=expect_denied(lambda:hr.analytics.employees.update_one({'_id':1},{'$set':{'salary':1}}))
  with client() as unauth:checks['anonymous_read_denied']=expect_denied(lambda:unauth.analytics.orders.find_one())
  with client('app_reader','deliberately-wrong-lab-password') as wrong:checks['wrong_password_rejected']=expect_denied(lambda:wrong.analytics.orders.find_one(),18)
  with client('lab_admin',values['lab_admin'],tls=False) as plain:
   try:plain.analytics.orders.find_one()
   except (ServerSelectionTimeoutError,ConnectionFailure):checks['plaintext_rejected']={'passed':True,'outcome':'transport rejected; requireTLS verified on server'}
   else:raise AssertionError('Plaintext connection unexpectedly succeeded')
  with client('lab_admin',values['lab_admin'],ca=CERTS/'wrong-ca.crt') as badca:
   try:badca.analytics.orders.find_one()
   except ServerSelectionTimeoutError as e:
    if 'CERTIFICATE_VERIFY_FAILED' not in str(e) and 'certificate verify failed' not in str(e).lower():raise
    checks['untrusted_ca_rejected']={'passed':True,'outcome':'certificate verification failed'}
   else:raise AssertionError('Untrusted CA unexpectedly accepted')
  assert admin.analytics.orders.count_documents({})==10
  checks['tls_read_after_negative_tests']={'passed':True,'count':10}
  context=ssl.create_default_context(cafile=str(CERTS/'ca.crt'));context.load_cert_chain(str(CERTS/'client.pem'))
  with socket.create_connection((HOST,PORT),timeout=5) as raw:
   with context.wrap_socket(raw,server_hostname=HOST) as sock:
    tls={'version':sock.version(),'cipher':sock.cipher()[0],'hostname_verified':True,'client_certificate_presented':True}
  roles=admin.admin.command('rolesInfo',[{'role':r,'db':'admin'} for r in ['ordersReader','ordersWriter','hrReader']],showPrivileges=True)['roles']
  evidence={'experiment':12,'passed':True,'at':now(),'environment':environment(),'server_version':version,
    'checks':checks,'tls':tls,'certificates':certificates.metadata(CERTS),'roles':roles,
    'method':'MongoDB auth and required TLS together; SCRAM passwords plus CA-validated client/server TLS certificates. No allowInvalidCertificates or allowInvalidHostnames. Secret material excluded from image and submission ZIP.',
    'cia':{'confidentiality':'TLS, collection-scoped RBAC and salary-redacted view','integrity':'Unauthorized writes rejected; authenticated scoped CRUD verified','availability':'Server remains reachable after negative tests. Single-node lab does not demonstrate failover, backups or production HA.'}}
  assert all(v['passed'] is True for v in checks.values())
  save('evidence.json',evidence);save('run_state.json',{'status':'passed','at':now()})
  print('SCREENSHOT 01: RBAC and negative tests');print(json.dumps(checks,indent=2))
  print('SCREENSHOT 02: TLS and certificate chain');print(json.dumps({'tls':tls,'certificates':evidence['certificates']},indent=2))
  print('EXERCISE 12 PASSED. Secrets not printed. Next: PUBLISH.ps1.')
