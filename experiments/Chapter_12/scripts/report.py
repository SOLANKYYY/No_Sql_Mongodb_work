import re,json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from common import ROOT,RESULTS,EXPERIMENT,load
TITLE={11:'Sharding & Horizontal Scalability',12:'Database Security & the CIA Triad'}[EXPERIMENT]

def validate():
 e=load('evidence.json');state=load('run_state.json')
 if e.get('experiment')!=EXPERIMENT or e.get('passed') is not True or state.get('status')!='passed':raise ValueError('Run RUN.ps1 successfully first.')
 if not e.get('server_version') or not e.get('checks'):raise ValueError('Missing measured evidence.')
 if EXPERIMENT==11:
  expected={'counts','ranged_hotspot','hashed_spread','routing_verified'}
  if set(e['checks'])!=expected or not all(v is True for v in e['checks'].values()):raise ValueError('Incomplete sharding checks')
  for n in ('hotspot_data','even_data'):
   if e['distribution'][n]['total_count']!=10000:raise ValueError('Expected 10,000 documents per collection')
  if [x['shard_count'] for x in e['explain']]!=[1,2,1,2]:raise ValueError('Routing evidence incomplete')
 else:
  required={'reader_find_and_aggregate','reader_write_denied','reader_base_salary_denied','reader_other_collection_denied','salary_view_redacted','writer_scoped_crud','writer_other_collection_denied','writer_salary_denied','hr_salary_visible','hr_write_denied','anonymous_read_denied','wrong_password_rejected','plaintext_rejected','untrusted_ca_rejected','tls_read_after_negative_tests','auth_enabled','tls_required'}
  if not required.issubset(e['checks']) or not all(v.get('passed') is True for v in e['checks'].values()):raise ValueError('Incomplete security checks')
  if not e['tls']['hostname_verified']:raise ValueError('TLS hostname verification missing')
 print('Required measured evidence passed.')
 return e

def publication():
 p=load('published.json');image=p.get('image');url=p.get('docker_url');digest=p.get('digest')
 if not isinstance(image,str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]+/nosql-exercise'+str(EXPERIMENT)+':exercise'+str(EXPERIMENT),image):raise ValueError('Invalid image name')
 repo=image.split(':')[0]
 if url!='https://hub.docker.com/r/'+repo or not isinstance(digest,str) or not re.fullmatch(re.escape(repo)+r'@sha256:[a-f0-9]{64}',digest) or p.get('verified_pull') is not True:raise ValueError('Publish and verify the image before generating the final PDF')
 return p

def build(path,e=None,p=None):
 for name,f in [('DejaVu','DejaVuSans.ttf'),('DejaVuBold','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(name,str(ROOT/'scripts/fonts'/f)))
 st=getSampleStyleSheet();st.add(ParagraphStyle(name='Body',fontName='DejaVu',fontSize=9,leading=13,spaceAfter=7));st.add(ParagraphStyle(name='SmallCell',fontName='DejaVu',fontSize=7.5,leading=10));st['Title'].fontName='DejaVuBold';st['Title'].fontSize=23;st['Title'].leading=29;st['Heading2'].fontName='DejaVuBold';st['Heading2'].keepWithNext=True;st['Heading2'].textColor=colors.HexColor('#123c57')
 story=[]
 def para(t):story.append(Paragraph(escape(str(t)),st['Body']))
 def heading(t):story.append(Paragraph(escape(t),st['Heading2']))
 def table(rows,widths):
  cells=[[Paragraph(escape(str(x)),st['SmallCell']) for x in row] for row in rows]
  t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dceaf2')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#b9c7d0')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.append(t);story.append(Spacer(1,10))
 student=load('student.json') if (RESULTS/'student.json').exists() else {'name':'Solanki Om Narendra','roll':'24BTRCL190'}
 story.append(Paragraph('EXERCISE '+str(EXPERIMENT),st['Heading2']));story.append(Paragraph(escape(TITLE),st['Title']))
 para(student['name']+' | '+student['roll']+' | 5AIMLB');para('23CSE528: NoSQL Database using MongoDB')
 heading('Final measured submission' if e else 'Lab guide - run results pending')
 if e:
  para('Measured at '+e['at']+' | MongoDB '+e['server_version']);para('Docker Hub: '+p['docker_url']);para('Image: '+p['image']);para('Verified pull digest: '+p['digest']);para('Evidence: results/evidence.json. Report generated after successful tests and a verified image pull.')
 else:
  para('This guide contains the method and instructions. It is not evidence that the lab or Docker upload has completed. PUBLISH.ps1 generates the final PDF from your successful run and verified Docker Hub image.')
 heading('Objective and method')
 if EXPERIMENT==11:
  para('Evaluate four e-commerce shard keys, then compare a timestamp hotspot with a hashed key using two real shards. The kit inserts 10,000 identical synthetic documents into each collection and records per-shard collStats and executionStats explain output.')
  para('Topology: runner -> mongos -> shardA and shardB; mongos reads routing metadata from cfg. Each replica set has one member to fit a laptop. This is not a highly available production cluster. Services are private to the Compose network, with no host ports exposed.')
  para('Controlled experiment: pause the balancer during measurement, split the timestamp range and place its empty historical chunk on shardB. All generated recent timestamps fall on shardA. The hashed collection starts with four distributed chunks. This exposes routing mechanics without claiming that 10,000 small records trigger automatic splitting or rebalancing.')
  heading('Lab 11.1 - shard key decision matrix')
  from lab import decision_matrix
  m=e['matrix'] if e else decision_matrix()
  para(m['workload']);table([['Key','Distinct values','Distribution','Query targeting','Trade-off']]+m['rows'],[69,46,115,117,137]);para(m['recommendation'])
  para('Dates are unique to the second in this fixture; day-only dates would have much lower cardinality. Distribution depends on chunk placement and value frequency, not cardinality alone. Hashing spreads distinct values but cannot split one frequently repeated customer value.')
  heading('Lab 11.2 - measured distribution and query routing')
  if e:
   rows=[['Collection','Shard','Documents','Data bytes','Storage bytes']]
   for n,v in e['distribution'].items():
    for shard,s in v['shards'].items():rows.append([n,shard,s['count'],s['size_bytes'],s['storage_bytes']])
   table(rows,[120,68,80,100,116]);table([['Query','Matched','Target shards']]+[[x['label'],x['matched'],', '.join(x['shards'])] for x in e['explain']],[260,60,164])
   para('Insertion durations (ms): '+json.dumps(e['insert_ms']));para('All count, distribution and routing assertions passed. Raw collStats, full explain trees and chunk boundaries are retained in evidence.json.')
  else:para('RUN.ps1 measures counts, data sizes, storage sizes, insertion duration and shard targeting. It checks 10,000 documents in each collection; one shard holds all recent range inserts, both shards hold hashed records, and four query routing counts are 1, 2, 1 and 2. Actual measurements appear in the final report.')
  para('The identical timestamp range matches 600 records on either collection. It targets one range shard but broadcasts on the user_id-hashed collection. A user_id equality lookup targets one hash shard; a user_id range broadcasts. Ranged keys suit bounded range locality; monotonically increasing writes can bottleneck the newest chunk. This small controlled test is not a throughput capacity benchmark.')
  heading('Activity 11.1 - resharding, scoped to MongoDB 7.0')
  para('Resharding is available from MongoDB 5.0. Before starting, assess the new key, query patterns, unique indexes, backups and free disk space. Confirm writeConcernMajorityJournalDefault=true. On mongos run db.adminCommand({reshardCollection: "shop.orders", key: {customer_id: "hashed"}}). Monitor currentOp, wait for completion, then validate the new key, routing and application behavior. Resharding copies and catches up data before a brief write-blocking cutover; allow for operational impact.')
  para('Only one collection can be resharded at a time. MongoDB 7.0 does not reshard time-series collections. Avoid concurrent collection/index changes and shard topology changes; required temporary storage and unique-index compatibility must be checked. Same-key redistribution is a later-version feature, not part of this 7.0 kit. This activity is research; the lab does not claim a measured resharding run.')
 else:
  para('Configure authentication and collection-scoped RBAC; verify allowed reads and writes as well as denied operations. Require TLS, validate the certificate chain and hostname, and demonstrate rejection of plaintext and an untrusted CA.')
  heading('Lab 12.1 - least privilege and field redaction')
  table([['Identity','Allowed access','Denied access'],['lab_admin','Root administration for isolated setup','Used only for setup and verification'],['app_reader','find / ordinary aggregation on analytics.orders and employee_public view','Writes, base employees, restricted collection'],['app_writer','find, insert, update, remove on analytics.orders','Other collections including employee salary'],['hr_user','find on analytics.employees including salary','Updates to employee records']],[90,215,179])
  para('Custom roles are created in admin with explicit collection resources. Ordinary read-only aggregation uses find permission; aggregate is not a MongoDB privilege action. The employee_public view applies {$project: {salary: 0}}. Non-HR users have access to the view but no read access to its base collection. A view alone is insufficient if base-collection access is also granted.')
  heading('Lab 12.2 - certificate chain and TLS')
  para('A private lab CA signs distinct server and client certificates. The server certificate includes SAN DNS:mongo, DNS:localhost and IP:127.0.0.1, with serverAuth usage; the client certificate uses clientAuth. MongoDB runs with --auth and --tlsMode requireTLS. PyMongo verifies the CA and hostname and presents a client certificate; database roles still use SCRAM credentials.')
  para('Certificate generation is automated with cryptography. Private keys and passwords are generated locally and kept outside the image and submission archive. Preserve .secrets together with the TLS and MongoDB volumes to restart the same deployment. Lab certificates are not a replacement for an organization-managed production PKI.')
  if e:
   table([['Verification','Result']]+[[k.replace('_',' '),'PASS'+(' (code '+str(v['error_code'])+')' if 'error_code' in v else '')] for k,v in e['checks'].items()],[365,119])
   para('Negotiated TLS: '+e['tls']['version']+' / '+e['tls']['cipher'])
   for n,c in e['certificates'].items():para(n.upper()+': '+c['subject']+'; issuer '+c['issuer']+'; expires '+c['not_after']+'; SHA-256 '+c['sha256'])
  else:para('Measured RBAC checks, denial codes, TLS protocol/cipher, public certificate fingerprints and expiry dates appear in the final report after RUN.ps1 passes.')
  heading('CIA triad and limits')
  para('Confidentiality: encrypted transport, role scopes and salary redaction. Integrity: authenticated collection CRUD and rejection of unauthorized writes. Availability: successful access after negative tests shows the server remains responsive; this single-node exercise does not demonstrate failover, backups or disaster recovery.')
 heading('Execution and submission')
 para('Extract the ZIP into its own folder. Open PowerShell in the folder containing SETUP.ps1. Start Docker Desktop (Linux containers). Run each command separately and stop if any fails:')
 for command in ['SETUP.ps1 -AllowSystemDrive','RUN.ps1','PUBLISH.ps1','COLLECT.ps1']:para('powershell -NoProfile -ExecutionPolicy Bypass -File .\\'+command)
 para('After RUN, put your actual screenshots in screenshots/. PUBLISH validates results, builds and pushes a separate image, verifies a pull and generates results/Exercise_'+str(EXPERIMENT)+'_Final_Report.pdf. COLLECT creates Experiment_'+str(EXPERIMENT)+'_Completed_Submission.zip. Submit the final PDF with its Docker Hub URL; retain the ZIP and published image for demonstration. Use DEMONSTRATE.ps1 to rerun using the published image.')
 if e:
  files=sorted(Path('/screenshots').glob('*')) if Path('/screenshots').exists() else sorted((ROOT/'screenshots').glob('*'))
  files=[f for f in files if f.suffix.lower() in ('.png','.jpg','.jpeg')]
  if files:
   heading('Actual screenshots supplied with this run')
   from PIL import Image as PILImage
   for f in files:
    story.append(PageBreak());para(f.name)
    with PILImage.open(f) as im:w,h=im.size
    ratio=min(484/w,620/h);story.append(Image(str(f),width=w*ratio,height=h*ratio))
  else:para('No screenshot files were supplied. The tables above are generated from measured JSON evidence; add screenshots and run REPORT.ps1 before collecting if screenshots are required.')
 heading('References and reproducibility')
 urls=['https://github.com/sujeetjagtap/NoSQL-Databases-using-MongoDB/tree/main/chapter-'+str(EXPERIMENT)]
 urls+=['https://www.mongodb.com/docs/v7.0/core/sharding-reshard-a-collection/','https://www.mongodb.com/docs/manual/core/hashed-sharding/'] if EXPERIMENT==11 else ['https://www.mongodb.com/docs/manual/reference/privilege-actions/','https://www.mongodb.com/docs/manual/tutorial/configure-ssl/']
 for u in urls:para(u)
 para('Implementation: scripts/lab.py; supporting files: Dockerfile, docker-compose.yml, scripts/report.py and tests/. Requirements and MongoDB image versions are pinned. Full source is included in the submission folder.')
 def footer(canvas,doc):
  canvas.setFont('DejaVu',8);canvas.setFillColor(colors.HexColor('#51606d'));canvas.drawString(42,25,'Exercise '+str(EXPERIMENT)+' | '+student['roll']);canvas.drawRightString(553,25,str(doc.page))
 path.parent.mkdir(parents=True,exist_ok=True)
 SimpleDocTemplate(str(path),pagesize=(595,842),rightMargin=55,leftMargin=56,topMargin=40,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
 print('Report saved:',path)

def report():build(RESULTS/('Exercise_'+str(EXPERIMENT)+'_Final_Report.pdf'),validate(),publication())
def guide():build(ROOT/'docs'/('Exercise_'+str(EXPERIMENT)+'_Lab_Guide.pdf'))
