"""Create preparation documentation or four evidence-gated final submission PDFs."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from xml.sax.saxutils import escape
import json,re

FILES=['lab14_1_monitoring.json','lab14_1_webhook.json','lab14_2_restore.json','lab14_2_pitr.json','lab14_2_benchmarks.json','lab14_2_retention.json','lab14_2_schedule.json','lab15_1_api.json','lab15_2_migration.json','lab16_1_models.json','lab16_2_hybrid.json','lab16_2_unit_tests.json']

def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def validate(root,published=False):
    root=Path(root);e={}
    for name in [f for f in FILES if f.startswith('lab15_')]:
        if not (root/name).is_file():raise ValueError('Missing measured evidence: '+name)
        d=load(root/name)
        if d.get('passed') is not True:raise ValueError('Evidence is not passed: '+name)
        e[name]=d
    if 15 == 14:
        m=e[FILES[0]]
        if m.get('sample_count',0)<3 or m.get('interval_seconds')!=30 or len(m.get('samples',[]))<3:raise ValueError('Three 30-second live monitoring samples required.')
        r=e['lab14_2_restore.json']
        if r.get('before')!=r.get('after') or r.get('documents')!=1000 or r.get('before',{}).get('sha256')==r.get('modified',{}).get('sha256'):raise ValueError('Restore integrity evidence incomplete.')
        p=e['lab14_2_pitr.json']
        if p.get('expected')!=p.get('restored') or not p.get('good_write_included') or not p.get('bad_write_excluded'):raise ValueError('PITR validation missing.')
        b=e['lab14_2_benchmarks.json']
        if [r.get('documents') for r in b.get('rows',[])]!=[1000,10000,100000] or not all(r.get('passed') and r.get('before')==r.get('after') for r in b['rows']):raise ValueError('Three verified benchmark sizes required.')
    if 15 == 15:
        a=e['lab15_1_api.json'];g=e['lab15_2_migration.json']
        if not all(a.get('checks',{}).values()) or len(a.get('checks',{}))<10:raise ValueError('API checks incomplete.')
        if not (g.get('tenants')==5 and g.get('documents_per_tenant')==100 and g.get('idempotent') and g.get('source_unchanged')):raise ValueError('Migration evidence incomplete.')
    if 15 == 16:
        model=e['lab16_1_models.json']
        if set(model.get('observed',{}))!={'mongodb','cassandra','neo4j'} or not all(v==model.get('expected') for v in model['observed'].values()):raise ValueError('Live three-engine model evidence required.')
        if not e['lab16_2_hybrid.json'].get('analysis',{}).get('complete'):raise ValueError('All live hybrid backends must pass.')
    if published:
        p=load(root/'published.json');s=load(root/'student.json')
        publications=p.get('experiments',{})
        for n in (15,):
            item=publications.get(str(n),{})
            match=re.fullmatch(r'([a-z0-9][a-z0-9_-]+)/nosql-exercise'+str(n)+':exercise'+str(n),item.get('image',''))
            if not match or item.get('verified_pull') is not True:
                raise ValueError('Verified separate publication required for Exercise '+str(n))
            repo=match[1]+'/nosql-exercise'+str(n)
            if item.get('docker_url')!='https://hub.docker.com/r/'+repo or not re.fullmatch(re.escape(repo)+r'@sha256:[0-9a-f]{64}',item.get('digest','')):
                raise ValueError('Invalid repository URL or digest for Exercise '+str(n))
        if not s.get('name') or not s.get('roll'):raise ValueError('Student identity required.')
        e.update({'published.json':p,'student.json':s})
    return e

def generate(root,out,preparation=False):
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer,PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    fonts=Path(__file__).parent/'fonts'
    for name,filename in [('Lab','DejaVuSans.ttf'),('Bold','DejaVuSans-Bold.ttf'),('Mono','DejaVuSansMono.ttf')]:pdfmetrics.registerFont(TTFont(name,str(fonts/filename)))
    pdfmetrics.registerFontFamily('Lab',normal='Lab',bold='Bold',italic='Lab',boldItalic='Bold')
    e={} if preparation else validate(root,True)
    identity=e.get('student.json',{'name':'Solanki Om Narendra','roll':'24BTRCL190'})
    navy=colors.HexColor('#163348');teal=colors.HexColor('#087E8B');pale=colors.HexColor('#EDF5F7')
    styles={
      'body':ParagraphStyle('body',fontName='Lab',fontSize=9.4,leading=14,spaceAfter=9,textColor=navy),
      'small':ParagraphStyle('small',fontName='Lab',fontSize=7.7,leading=11,spaceAfter=6,textColor=navy),
      'h1':ParagraphStyle('h1',fontName='Bold',fontSize=22,leading=28,spaceAfter=17,textColor=navy),
      'h2':ParagraphStyle('h2',fontName='Bold',fontSize=12,leading=16,spaceBefore=8,spaceAfter=8,textColor=teal),
      'cell':ParagraphStyle('cell',fontName='Lab',fontSize=8.0,leading=11.5,textColor=navy),
      'code':ParagraphStyle('code',fontName='Mono',fontSize=7.4,leading=11,spaceAfter=12,backColor=pale,borderPadding=7)}
    def build(chapters,filename):
        story=[]
        def p(text,style='body'):story.append(Paragraph(text,styles[style]))
        def sub(text):p(text,'h2')
        def page(title):story.append(PageBreak());p(title,'h1')
        def code(text):p(escape(text).replace('\n','<br/>'),'code')
        def table(rows,widths=(175,320)):
            cells=[[Paragraph(escape(str(v)),styles['cell']) for v in r] for r in rows]
            t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#C8E3E9')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,pale]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.extend([t,Spacer(1,10)])
        title='Exercises '+', '.join(map(str,chapters)) if len(chapters)>1 else 'Exercise '+str(chapters[0])
        p(title,'h2');p('NoSQL Database<br/>Laboratory Submission','h1')
        p('PREPARATION REPORT - LOCAL EXECUTION PENDING' if preparation else 'FINAL REPORT - RECORDED CHECKS PASSED','h2')
        table([['Student','Details'],['Name',identity['name']],['Roll / register number',identity['roll']],['Subject','NoSQL Databases using MongoDB'],['Contents','Multi-tenant SaaS and tenant migration'],['Prepared / generated',datetime.now(timezone(timedelta(hours=5,minutes=30))).strftime('%d %B %Y, %H:%M IST')]])
        if preparation:
            p('<b>This is the runnable kit and preparation documentation.</b> Database runs and publication have not yet been completed for these experiments. The kit records actual observations and generates separate final PDFs only after all required checks and Docker Hub push/pull succeed.')
            sub('Run order on the student computer')
            code('SETUP.ps1\nRUN_14.ps1\nRUN_15.ps1\nRUN_16.ps1\nPUBLISH.ps1\nCOLLECT.ps1')
            p('Run each using: powershell -NoProfile -ExecutionPolicy Bypass -File .\\SCRIPT.ps1. Extract on E: first and relocate Docker disk storage as described in docs/E_DRIVE_SETUP.md.')
        else:
            sub('Published Docker submission')
            for n in chapters:
                pub=e['published.json']['experiments'][str(n)]
                p('Exercise '+str(n),'h2')
                p('<link href="'+pub['docker_url']+'" color="#087E8B">'+pub['docker_url']+'</link>')
                code(pub['image']);p('Verified digest: '+pub['digest'],'small')
                p('Push/pull check: '+pub['timestamp'],'small')
            p('Each experiment has its own Docker Hub repository and tag. This repository contains the standalone code for this experiment.')
        p('The databases are dedicated local classroom services. The kit publishes no MongoDB or Cassandra port; its API and Neo4j ports bind to localhost. Database authentication is disabled for the isolated demonstration deployment. This is not a hardened production installation.','small')
        if 14 in chapters:
            page('14 / Production service management')
            sub('Lab 14.1 - Monitoring and alerting')
            p('The monitor reuses one PyMongo client, samples serverStatus every 30 seconds and appends timestamped records to logs/metrics.log. It displays connections, operation counters, WiredTiger cache size and dirty bytes, replica members and secondary lag.')
            p('The interval cache-hit estimate is 100 x (1 - change in pages read into cache / change in pages requested). Missing counters, the first sample, idle intervals and server resets produce N/A. Occupancy is reported separately. The estimate is a page-counter proxy, not a universal per-query hit-rate guarantee.')
            p('Warnings trigger below 80% cache hit estimate or above 10 seconds secondary lag. Lag is the time difference between primary and secondary optimeDate values. The small default replica set has one member, so live secondary lag is N/A. A labelled fixture tests the lag and cache warning paths.')
            p('The webhook activity performs a real HTTP POST to a local receiver with synthetic 70% cache / 12-second lag inputs. A private WEBHOOK_URL can optionally deliver notifications to Slack or Discord; no external delivery is claimed unless its result is recorded.')
            if preparation:table([['Evidence to collect','Status'],['Three live monitoring samples','Pending local execution'],['Threshold boundary and webhook checks','Pending local execution']])
            else:
                m=e['lab14_1_monitoring.json'];w=e['lab14_1_webhook.json']
                table([['Recorded check','Result'],['Live samples',m['sample_count']],['Interval',str(m['interval_seconds'])+' seconds'],['Elapsed measurement',str(m['elapsed_seconds'])+' seconds'],['Local webhook delivery',w['local_delivery']['delivered']],['Alert test type',w['evidence_type']],['External webhook',w.get('external_delivery','Not configured / not measured')]])
            sub('Lab 14.2 - Backup and recovery design')
            p('A timestamped mongodump snapshot is created, all 1,000 test documents are modified, and mongorestore --drop restores the original collection. Verification compares both count and a deterministic content checksum including _id. The original test data remains in the dedicated exercise14 database.')
            p('A separate controlled PITR drill creates a full replica-set dump with --oplog, captures subsequent oplog entries, and restores into the isolated mongo-restore instance. --oplogLimit excludes the known bad write while retaining the approved write. This is a bounded demonstration with no concurrent application writers, not a continuous production PITR service.')
            page('14 / Measurements and recovery objectives')
            p('The benchmark seeds 1,000, 10,000 and 100,000 documents of approximately 1 KB each. It records actual BSON size, compressed backup size, backup time, restore time and recovery verification time. Temporary benchmark archives are removed after successful verification to reduce disk usage.')
            if preparation:table([['Document count','Backup / restore / verified recovery'],['1,000','Pending measured execution'],['10,000','Pending measured execution'],['100,000','Pending measured execution']])
            else:
                rows=e['lab14_2_benchmarks.json']['rows']
                table([['Docs','Backup (s)','Restore (s)','Verified recovery (s)'],*[[r['documents'],f"{r['backup_seconds']:.3f}",f"{r['restore_seconds']:.3f}",f"{r['recovery_verified_seconds']:.3f}"] for r in rows]],(75,125,125,170))
                table([['Integrity result','Observed'],['Snapshot count/checksum match',e['lab14_2_restore.json']['before']==e['lab14_2_restore.json']['after']],['PITR approved write included',e['lab14_2_pitr.json']['good_write_included']],['PITR bad write excluded',e['lab14_2_pitr.json']['bad_write_excluded']],['Seven-day retention fixture passed',e['lab14_2_retention.json']['passed']],['Initial scheduled backup completed',e['lab14_2_schedule.json']['passed']]])
            sub('Scheduling, retention and interpretation')
            p('The scheduler runs an immediate backup and then schedules starts at hourly intervals. It removes only owned, completed backup directories older than seven days; unrelated, incomplete and symlinked paths are preserved. A fixture checks the retention boundary without waiting seven days.')
            p('Nominal snapshot RPO is one hour when scheduled backups succeed. Completion time, missed runs, sleep and outages can increase exposure. The observed scheduler evidence is its initial actual backup plus the configured hourly interval; it is not a claim that an hour elapsed during assessment.')
            p('Restore duration and restore-plus-integrity/read-readiness duration are measured separately. A production RTO must additionally include application restart, routing and infrastructure recovery. This kit has no separate production application restart measurement for Lab 14.2.')
            p('Backing up to E: avoids filling C:, but another partition on the same physical disk is not an independent disaster-recovery copy. Production recovery also needs protected off-machine backups and tested retention.','small')
        if 15 in chapters:
            page('15 / Multi-tenant SaaS API')
            sub('Lab 15.1 - Identity, CRUD and roles')
            p('FastAPI exposes authenticated task creation, listing, individual reads, updates and deletion. Login verifies scrypt password hashes and issues a signed, expiring JWT. The API validates issuer, audience, expiry and subject; the server-side user record supplies tenant and role.')
            p('Every task query filters tenant_id. A regular user also filters owner_id; an administrator can manage all tasks only within the same tenant. Request bodies cannot set tenant, owner or role. Compound tenant/date and tenant/owner/date indexes support the corresponding query patterns.')
            p('The MongoDB rate limiter uses atomic find_one_and_update counters for a fixed 60-second window. A TTL date removes old buckets, but authorization depends on the bucket key and count rather than timely TTL deletion. The default is 20 task requests per user per window. Fixed windows can allow bursts across adjacent boundaries.')
            if preparation:table([['Live checks','Status'],['CRUD, cross-tenant denial and owner/admin access','Pending'],['30 concurrent requests: 20 allowed, 10 limited','Pending'],['Spoofed identity and invalid JWT rejected','Pending']])
            else:
                a=e['lab15_1_api.json'];table([['Security check','Passed'],*[[k,v] for k,v in a['checks'].items()]])
            sub('Interactive API demonstration')
            p('Open http://localhost:8015/docs while the API container is running. POST /auth/token accepts a seeded username and the private DEMO_PASSWORD from .env. Use the returned bearer token with Authorize. Demo users include alice, bob, admin-a, carol and admin-b. Do not include tokens or .env in submission screenshots.')
            page('15 / Tenant migration and tradeoffs')
            p('Lab 15.2 seeds five tenants with 100 tasks each in one shared collection. It copies each tenant into tasks_tenant_0 through tasks_tenant_4, preserves document IDs and compares counts and content hashes. Collection validators reject other tenant IDs. A repeat copy proves idempotency, and a rollback drill drops one copied collection while preserving the source, then rebuilds the copy.')
            if preparation:table([['Validation','Status'],['500 source documents and 100 per tenant','Pending'],['Content hashes, no leakage and repeat-copy identity','Pending'],['Query performance measurements','Pending']])
            else:
                g=e['lab15_2_migration.json'];table([['Tenant','Source count','Target count','Valid'],*[[r['tenant'],r['source_count'],r['target_count'],r['passed']] for r in g['first_copy']]],(180,105,105,105))
                table([['Operation','Shared median ms','Per-tenant median ms'],*[[name,f"{v['shared']['median_ms']:.3f}",f"{v['collection_per_tenant']['median_ms']:.3f}"] for name,v in g['timings'].items()]],(225,135,135))
                p('Idempotent: '+str(g['idempotent'])+'; source unchanged: '+str(g['source_unchanged'])+'; rollback preserves source: '+str(g['rollback_source_preserved'])+'.')
            table([['Strategy','Suitable use and limitation'],['Shared collection','Many tenants with a common schema and frequent cross-tenant analytics; every application query must enforce tenancy.'],['Collection per tenant','Per-tenant backup and schema management; more namespaces, indexes and cross-tenant query fan-out.'],['Database per tenant','Separate database authorization and administration where required; greater operational overhead.']])
            p('Recommendation: begin with document-level isolation when scale, common schemas and analytics favour it; choose stronger namespace separation for specific tenant administration requirements. This migration is an offline copy exercise with no concurrent writes or API cutover. A live migration also needs change capture, reconciliation and controlled routing changes.')
        if 16 in chapters:
            page('16 / Equivalent models in three databases')
            p('Lab 16.1 uses one university enrollment dataset: four students, three courses and six enrollments. MongoDB stores students with embedded course IDs and courses with embedded student rosters. Cassandra uses two query-oriented tables partitioned by student_id or course_id. Neo4j stores Student and Course nodes connected by ENROLLED_IN relationships.')
            table([['Equivalent query','Expected dataset answer'],['Courses for Alice / S1','C1, C2'],['Students in C1','S1, S2'],['Students sharing a course with S1','S2, S3']])
            p('MongoDB retrieves documents and matches course arrays; Cassandra uses prepared partition-key queries and joins the peer results in Python; Neo4j performs relationship pattern matching. The integration run compares all answers against the same expected sets. No in-memory database fallback is used for final evidence.')
            sub('Hybrid enrollment activity')
            p('MongoDB supplies the operational student record, Cassandra records timestamped enrollment audit events and Neo4j traverses course prerequisite chains. The fixture expects two audit events for S1 and C1/C2 as prerequisites of C3. A production version needs durable event delivery, idempotency and reconciliation across stores.')
            if preparation:table([['Backends / activity','Status'],['MongoDB, Cassandra and Neo4j query equality','Pending live run'],['Audit and prerequisite chain checks','Pending live run']])
            else:
                mo=e['lab16_1_models.json'];table([['Backend','Queries equal expected','Median query-set ms'],*[[name,data==mo['expected'],f"{mo['timings'][name]['median_ms']:.3f}"] for name,data in mo['observed'].items()]],(120,200,175))
                p('Hybrid enrollment checks: '+escape(str(mo['hybrid_enrollment_activity'])),'small')
            sub('Query complexity and expected performance')
            p('MongoDB offers flexible document retrieval; Cassandra makes known partition-key access direct but requires denormalized tables for alternate queries; Neo4j expresses multi-hop relationships compactly. These are design characteristics, not a universal ranking. Measured local timings reflect this tiny dataset and include client round trips.')
            page('16 / Hybrid fraud query service')
            table([['Service method','Backend and access pattern'],['get_transaction(txn_id)','MongoDB: unique indexed transaction lookup'],['get_user_profile(user_id)','Cassandra: latest events in one user partition, ordered by time'],['detect_fraud_rings(user_id, max_hops)','Neo4j: bounded connected-account traversal and directed cycles']])
            p('The service maintains long-lived database clients/sessions. PyMongo uses its standard pool; Cassandra uses a Cluster/Session with four executor threads for metadata/control work; Neo4j limits the local connection pool to ten. Executor thread count is not the number of pooled Cassandra connections.')
            p('Each backend has its own circuit breaker. Three consecutive failures open it; calls are skipped for 30 seconds, then one probe may run. Success resets the breaker. The merged response identifies unavailable stores explicitly and preserves successful partial results; it never presents missing data as a successful empty answer.')
            p('Mock-based tests check routing, partial failure, open/skip/recovery transitions, threshold boundaries and identity filtering. Separate live integration checks require all three backends. Graph connectivity and cycles are investigation signals, not proof that a user committed fraud.')
            if preparation:table([['Evidence','Status'],['Mock tests','Executed during preparation; see docs/VALIDATION.md'],['Three-backend fraud workflow','Pending local execution'],['Transaction/profile/1-3 hop latency','Pending measured execution']])
            else:
                h=e['lab16_2_hybrid.json'];table([['Live workflow check','Passed'],*[[k,v] for k,v in h['checks'].items()]])
                table([['Method','Median ms','Mean ms'],*[[name,f"{v['median_ms']:.3f}",f"{v['mean_ms']:.3f}"] for name,v in h['latencies'].items()]],(245,125,125))
                p('Mock tests passed: '+str(e['lab16_2_unit_tests.json']['passed'])+'. Live performance measurements use 20 warm repetitions per method.','small')
        page('Reproduction, files and references')
        table([['File / directory','Purpose'],['SETUP.ps1 / RUN_14.ps1 / RUN_15.ps1 / RUN_16.ps1','Build, initialize and run this experiment'],['PUBLISH.ps1 / DEMONSTRATE.ps1','Publish three repositories and demonstrate a selected image'],['scripts/ / tests/','Implementation, report generator and mock tests'],['results/ / logs/ / backups/','Measured JSON, tables, logs and timestamped private backups'],['docs/E_DRIVE_SETUP.md','Move Docker disk storage and keep project outputs off C:']])
        p('The source code and project folders can live on E:. Named database volumes and image layers live inside Docker Desktop\'s Linux disk image, which must be relocated separately. Moving the ZIP alone does not move that disk. No cleanup script deletes previous exercise data.')
        p('Keep Docker Desktop running during labs. After publication, DEMONSTRATE.ps1 pulls the published image, exports the kit and reruns the experiments to produce fresh evidence. A published-image demonstration is a future action unless a completed run has been recorded.')
        sub('Instructor references')
        for n in chapters:
            link=f'https://github.com/sujeetjagtap/NoSQL-Databases-using-MongoDB/tree/main/chapter-{n}'
            p(f'<link href="{link}" color="#087E8B">Chapter {n}: instructor repository</link>','small')
        sub('Implementation references')
        links=[('Docker Desktop WSL data location','https://docs.docker.com/desktop/features/wsl/'),('MongoDB mongodump','https://www.mongodb.com/docs/database-tools/mongodump/'),('MongoDB mongorestore and oplog replay','https://www.mongodb.com/docs/database-tools/mongorestore/'),('FastAPI JWT authentication','https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/'),('Neo4j Docker configuration','https://neo4j.com/docs/operations-manual/current/docker/configuration/'),('Cassandra Python driver','https://docs.datastax.com/en/developer/python-driver/latest/api/cassandra/cluster/index.html')]
        for label,link in links:p(f'<link href="{link}" color="#087E8B">{label}</link>','small')
        p('The instructor screenshots define the assessed tasks where examples differ: 30-second monitoring, three backup sizes, five tenants with collection-per-tenant migration, and live university/fraud workflows across three database engines.','small')
        def footer(c,d):
            c.setStrokeColor(teal);c.line(50,795,545,795);c.setFillColor(navy);c.setFont('Lab',7.5);c.drawString(50,808,title+' | NoSQL Database Laboratory');c.line(50,42,545,42);c.drawString(50,29,identity['name']+' | '+identity['roll']);c.drawRightString(545,29,str(d.page))
        target=out/filename
        SimpleDocTemplate(str(target),pagesize=A4,leftMargin=50,rightMargin=50,topMargin=65,bottomMargin=58,title=title+' Report',author=identity['name']).build(story,onFirstPage=footer,onLaterPages=footer)
        print('Report saved: '+str(target))
    if preparation:build([15],'Exercise_15_Preparation_Report.pdf')
    else:
        for n in (15,):build([n],f'Exercise_{n}_Final_Report.pdf')

