"""Create preparation or final report; completed reports require measured evidence."""
import argparse
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import re
from xml.sax.saxutils import escape

FILES=['lab13_1_health.json','lab13_1_failover.json','lab13_1_monitoring.json','lab13_2_kubernetes.json']


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def members_ok(items):
    return (len(items)==3 and sum(m.get('state')=='PRIMARY' for m in items)==1
            and sum(m.get('state')=='SECONDARY' for m in items)==2
            and all(m.get('health')==1 for m in items))


def validate(root, published=False):
    evidence={}
    for name in FILES:
        path=root/name
        if not path.exists(): raise ValueError('Missing evidence: '+name)
        evidence[name]=load(path)
        if evidence[name].get('passed') is not True: raise ValueError('Failed evidence: '+name)
    h,f,m,k=[evidence[n] for n in FILES]
    if not (members_ok(h.get('members',[])) and h.get('authenticated_read_write') is True
            and h.get('unauthenticated_read_denied') is True): raise ValueError('Health/authentication details incomplete.')
    if not (f.get('old_primary') and f.get('new_primary') and f['old_primary']!=f['new_primary']
            and f.get('post_stepdown_successes',0)>0 and f.get('acknowledged_documents_preserved') is True
            and members_ok(f.get('members_after',[]))): raise ValueError('Failover details incomplete.')
    if not (m.get('exporter_up') is True and m.get('prometheus_target_up') is True
            and m.get('prometheus_mongodb_up')==1): raise ValueError('Monitoring details incomplete.')
    if not (k.get('old_pod_uid') and k.get('new_pod_uid') and k['old_pod_uid']!=k['new_pod_uid']
            and k.get('persistent_volumes_reused') is True and len(k.get('storage',[]))==3
            and members_ok(k.get('after',{}).get('members',[]))
            and k.get('after',{}).get('sentinel')=='survives-pod-recreation'):
        raise ValueError('Kubernetes recovery details incomplete.')
    for v in k['storage']:
        if not (v.get('uid_before') and v['uid_before']==v.get('uid_after')
                and v.get('volume_before') and v['volume_before']==v.get('volume_after')
                and v.get('phase')=='Bound'): raise ValueError('PVC/PV evidence incomplete.')
    if published:
        p=load(root/'published.json'); student=load(root/'student.json')
        match=re.fullmatch(r'([a-z0-9][a-z0-9_-]+)/mongodb-exercise13:exercise13',p.get('image',''))
        if not (match and p.get('verified_pull') is True and
                p.get('docker_url')=='https://hub.docker.com/r/'+match[1]+'/mongodb-exercise13' and
                re.fullmatch(re.escape(match[1])+r'/mongodb-exercise13@sha256:[0-9a-f]{64}',p.get('digest',''))):
            raise ValueError('Verified Docker publication metadata required.')
        if not student.get('name','').strip() or not student.get('roll','').strip():
            raise ValueError('Student name and roll number are required.')
        evidence['published.json']=p; evidence['student.json']=student
    return evidence


def build(root, output, draft=False):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    fonts=Path(__file__).parent/'fonts'
    for name,filename in [('LabSans','DejaVuSans.ttf'),('LabBold','DejaVuSans-Bold.ttf'),('LabMono','DejaVuSansMono.ttf')]:
        pdfmetrics.registerFont(TTFont(name,str(fonts/filename)))
    pdfmetrics.registerFontFamily('LabSans',normal='LabSans',bold='LabBold',italic='LabSans',boldItalic='LabBold')
    e={} if draft else validate(root,published=True)
    h=e.get(FILES[0],{}); f=e.get(FILES[1],{}); m=e.get(FILES[2],{}); k=e.get(FILES[3],{})
    pub=e.get('published.json',{}); student=e.get('student.json',{})
    styles=getSampleStyleSheet()
    for st in styles.byName.values(): st.fontName='LabSans'
    for name in ['Title','Heading1','Heading2']: styles[name].fontName='LabBold'
    styles.add(ParagraphStyle(name='BodyLab',fontName='LabSans',fontSize=9.3,leading=14,spaceAfter=8,textColor=colors.HexColor('#243447')))
    styles.add(ParagraphStyle(name='SmallLab',fontName='LabSans',fontSize=7.8,leading=11,spaceAfter=5))
    styles.add(ParagraphStyle(name='CodeLab',fontName='LabMono',fontSize=7.1,leading=12,backColor=colors.HexColor('#edf2f7'),borderPadding=7,spaceAfter=10))
    styles['Title'].fontSize=27; styles['Title'].leading=33; styles['Title'].textColor=colors.HexColor('#123d5a')
    styles['Heading1'].textColor=colors.HexColor('#123d5a'); styles['Heading1'].spaceAfter=12
    styles['Heading2'].textColor=colors.HexColor('#147d92')
    story=[]
    def para(s,style='BodyLab'): story.append(Paragraph(s,styles[style]))
    def head(s): para(s,'Heading1')
    def sub(s): para(s,'Heading2')
    def code(s): para(escape(s).replace('\n','<br/>'),'CodeLab')
    def table(rows,widths=None):
        cells=[[Paragraph(escape(str(v)),styles['SmallLab']) for v in row] for row in rows]
        t=Table(cells,colWidths=widths or [165,330],hAlign='LEFT',repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e1eef3')),('VALIGN',(0,0),(-1,-1),'TOP'),
                              ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#c9d5df')),('LEFTPADDING',(0,0),(-1,-1),8),
                              ('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        story.append(t);story.append(Spacer(1,10))
    def val(d,key): return str(d.get(key,'Pending local execution'))
    def page(): story.append(PageBreak())

    para('EXERCISE 13','Heading2')
    para('Deploying MongoDB<br/>with Containers<br/>and the Cloud','Title')
    story.append(Spacer(1,18))
    para('PREPARATION REPORT - RUN BEFORE SUBMISSION' if draft else 'FINAL LAB SUBMISSION REPORT','Heading2')
    para('This package is a separate coursework project. It follows the supplied Chapter 13 references and the assignment screenshots.')
    table([['Submission field','Value'],['Student',student.get('name','Enter your name when PUBLISH.ps1 asks')],
           ['Roll / register number',student.get('roll','Enter your number when PUBLISH.ps1 asks')],
           ['Required work','Lab 13.1, Prometheus activity, Lab 13.2'],
           ['Execution status','Not executed in this preparation environment' if draft else 'All required recorded checks passed'],
           ['Docker publication','Pending your successful push/pull' if draft else pub['image']]])
    if draft:
        para('<b>This PDF is a preparation document, not evidence of completed labs.</b> Docker and Kubernetes were unavailable during preparation. Run the supplied scripts locally. PUBLISH.ps1 generates the final PDF only after required evidence and Docker publication checks succeed.')
    else:
        para('Docker Hub: <link href="'+escape(pub['docker_url'])+'" color="#147d92">'+escape(pub['docker_url'])+'</link>')
        para('Verified image digest: '+escape(pub['digest']),'SmallLab')
        para('Publication checked: '+escape(pub['timestamp']),'SmallLab')
    sub('Submission rule')
    para('Upload the completed Docker image to Docker Hub. Submit a PDF containing its Docker URL in Classroom. Keep the uploaded image available for the required demonstration. The instructor reference links are not your submission URL.')
    para('Generated: '+datetime.now(timezone(timedelta(hours=5,minutes=30))).strftime('%d %B %Y, %H:%M IST'),'SmallLab')

    page();head('01 / Docker Compose replica set')
    para('The deployment contains three data-bearing MongoDB services in replica set rs0. Each has its own persistent named volume. A common random keyfile authenticates the members; application credentials separately control database access.')
    sub('Implementation')
    para('A key-init container copies the generated key into a Linux volume and sets ownership 999:999 and permissions 0400. MongoDB nodes use --replSet rs0 and --keyFile. The client runs on the same Docker network as the advertised service names. Database ports are not exposed on the host.')
    para('Bootstrap runs inside mongo1 over localhost. It initiates rs0, waits for a primary, then creates the first administrator. Authenticated setup creates a database-scoped application user and a clusterMonitor user. This corrects the bootstrap ordering in the teaching shell script.')
    sub('Validation and observed output')
    table([['Check','Observed result'],['Three healthy data members','Pending local execution' if draft else ', '.join(x['state'] for x in h['members'])],
           ['Authenticated write/read',val(h,'authenticated_read_write')],['Unauthenticated protected read denied',val(h,'unauthenticated_read_denied')],
           ['Write concern',val(h,'writeConcern')],['Lab 13.1 health passed',val(h,'passed')]])
    sub('Failover test')
    para('A persistent PyMongo client continuously reads and writes while a separate connection steps down the primary. The test waits for a different primary, checks successful operations after stepdown and verifies acknowledged documents. Driver retries can hide a short interruption; zero transient errors is therefore a valid observation.')
    table([['Measurement','Observed value'],['Old primary',val(f,'old_primary')],['New primary',val(f,'new_primary')],
           ['Observed election seconds',val(f,'election_observed_seconds')],['Post-stepdown successful samples',val(f,'post_stepdown_successes')],
           ['Acknowledged documents preserved',val(f,'acknowledged_documents_preserved')]])
    para('Evidence: lab13_1_health.json and lab13_1_failover.json. No fixed sample measurements are substituted for actual observations.','SmallLab')

    page();head('02 / Prometheus monitoring activity')
    para('A Python exporter accompanies mongo1 and authenticates as a clusterMonitor user. It reads MongoDB server status and replica-set status, then exposes metrics for Prometheus. Prometheus scrapes the endpoint every five seconds.')
    table([['Metric','Meaning'],['mongodb_up','1 when the latest MongoDB scrape succeeded; 0 on a connection/command failure'],
           ['mongodb_connections','Current and available connections, labelled by kind'],['mongodb_opcounters','Cumulative MongoDB operation counts'],
           ['mongodb_member_state','Replica member state: 1 = PRIMARY, 2 = SECONDARY']])
    sub('Endpoints and observations')
    table([['Item','Value'],['Exporter','http://localhost:9216/metrics'],['Prometheus targets','http://localhost:9090/targets'],
           ['Exporter can read MongoDB',val(m,'exporter_up')],['Prometheus target UP',val(m,'prometheus_target_up')],
           ['Prometheus mongodb_up query',val(m,'prometheus_mongodb_up')],['Monitoring passed',val(m,'passed')]])
    para('Verification checks the exporter text, the Prometheus target status and the stored mongodb_up query result. This distinguishes an accessible HTTP endpoint from a working MongoDB scrape.')
    sub('Screenshot evidence')
    para('Open the exporter endpoint and capture mongodb_up plus member states. Open the Prometheus targets page and capture the MongoDB target as UP. On the query page, evaluate mongodb_up and capture value 1. Save as 03a-exporter.png and 03b-prometheus.png.')
    para('Evidence: lab13_1_monitoring.json and metrics.txt. The exporter is intentionally small and does not constitute a complete operational alerting platform.','SmallLab')

    page();head('03 / Kubernetes StatefulSet and recovery')
    para('Namespace exercise13 contains a headless Service, a scripts ConfigMap, one shared key Secret and a three-replica StatefulSet. mongo-0, mongo-1 and mongo-2 each have a stable DNS name and their own 1 GiB persistent volume claim.')
    sub('Keyfile and startup')
    para('Each initContainer copies the same Secret into its own memory-backed emptyDir and sets the MongoDB file permissions. emptyDir is shared only within a pod; it is not shared across pods. MongoDB data instead uses the PVC. Parallel startup and published not-ready addresses support bootstrap discovery.')
    sub('Recovery experiment')
    para('After establishing one PRIMARY and two SECONDARY members, the script writes a sentinel with w=3 and records mongo-2\'s UID and the claims/volume bindings. It deletes mongo-2, waits for a new ready pod, and directly reads the sentinel from the replacement member. The PVC and PV identities must remain unchanged.')
    table([['Recovery check','Observed result'],['Original pod UID',val(k,'old_pod_uid')],['Replacement pod UID',val(k,'new_pod_uid')],
           ['Original persistent volumes reused',val(k,'persistent_volumes_reused')],
           ['Sentinel read on replacement',val(k.get('after',{}),'sentinel')],['Recovery passed',val(k,'passed')]])
    if not draft:
        table([['Claim','Persistent volume','Phase']]+[[x['name'],x['volume_after'],x['phase']] for x in k['storage']],widths=[150,275,70])
    sub('Evidence interpretation')
    para('The test establishes automatic pod recreation, persistent volume reuse and retained replicated data. It does not establish durability after destroying a disk or losing the entire host. Both process responsiveness and MongoDB replication are checked separately.')
    para('Evidence: lab13_2_kubernetes.json. Capture the ready pods and bound claims, followed by the old/new UID and successful sentinel checks.','SmallLab')

    page();head('04 / Comparison and cloud reference')
    table([['Aspect','Docker Compose','Kubernetes'],['Identity','Stable service DNS','Stable pod ordinals + headless DNS'],
           ['Data storage','Named volume per service','PVC per StatefulSet replica'],['Recovery','Restart policy; compose up restores removed services','Controller restores desired pod count'],
           ['Primary election','MongoDB replica protocol','MongoDB replica protocol'],['Measured disruption','Primary stepdown','Deletion/recreation of mongo-2'],
           ['Complexity','Smaller local deployment','More cluster and storage configuration']],widths=[105,195,195])
    sub('Additional Atlas Terraform configuration')
    para('main.tf declares an Atlas project, an M0 tenant cluster, an exercise13-scoped user and one allowed client IP. It uses the provider v2 advanced_cluster schema and leaves M0-managed version and storage settings to Atlas. API and user secrets are read from local environment variables.')
    para('<b>Cloud status: configuration supplied; deployment not verified in this report.</b> The assignment references main.tf but lists the two local labs as its execution tasks. Terraform instructions are included separately. A successful validate or plan must not be labelled a deployed cluster.')
    sub('Production limitations')
    para('The teaching deployment includes authentication, persistent storage, restart behavior, resource limits, bounded logs and monitoring. A full production system also needs TLS, backups and restore testing, multi-host failure isolation, rotation and upgrade procedures, and alerting. Local nodes share one physical failure domain.')
    sub('Conclusion')
    para('Run the supplied scripts to establish whether the deployment and recovery meet the lab objectives. Results are pending.' if draft else 'The recorded local experiments passed the required authentication, replication, failover, monitoring and pod-recovery checks. The Docker image was pushed and pulled successfully; the report records its URL and digest for demonstration.')

    page();head('05 / Run, capture and submit')
    para('Extract the ZIP, start Docker Desktop using Linux containers, and open PowerShell in Exercise_13_Submission. No host Python or mongosh is required.')
    code('powershell -NoProfile -ExecutionPolicy Bypass -File .\\START.ps1')
    para('Enable Kubernetes in Docker Desktop and wait until it is running. Then:')
    code('powershell -NoProfile -ExecutionPolicy Bypass -File .\\LAB13_2.ps1\npowershell -NoProfile -ExecutionPolicy Bypass -File .\\PUBLISH.ps1\npowershell -NoProfile -ExecutionPolicy Bypass -File .\\COLLECT.ps1')
    para('PUBLISH asks for your name and roll number. It verifies required results, publishes the image, records a pulled digest and generates results/Exercise_13_Final_Report.pdf. Submit that final PDF in Classroom. Send Exercise_13_Results.zip and the requested screenshots to the chat for review.')
    para('For the demonstration, run DEMONSTRATE.ps1. It extracts the kit from the published image and runs both experiments using that image. Keep the original credential files when reusing existing volumes.')
    table([['Screenshot','What to capture'],['01 / 02','Replica health/authentication; changed primary and post-stepdown success'],
           ['03a / 03b','Exporter metrics and Prometheus target/query'],['04 / 05','Ready pods/bound claims; recreated pod and retained sentinel'],
           ['06','Docker Hub repository and exercise13 tag']])
    sub('Reference links')
    refs=[('Instructor Chapter 13','https://github.com/sujeetjagtap/NoSQL-Databases-using-MongoDB/tree/main/chapter-13'),
          ('Instructor docker-compose-production.yml','https://github.com/sujeetjagtap/NoSQL-Databases-using-MongoDB/blob/main/chapter-13/docker-compose-production.yml'),
          ('Instructor main.tf','https://github.com/sujeetjagtap/NoSQL-Databases-using-MongoDB/blob/main/chapter-13/main.tf'),
          ('MongoDB keyfile deployment','https://www.mongodb.com/docs/manual/tutorial/deploy-replica-set-with-keyfile-access-control/'),
          ('Kubernetes StatefulSets','https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/'),
          ('Terraform Atlas provider','https://registry.terraform.io/providers/mongodb/mongodbatlas/latest/docs/resources/advanced_cluster')]
    for label,url in refs: para('<link href="'+url+'" color="#147d92">'+label+'</link>','SmallLab')
    def footer(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#d5e0e8'));canvas.line(50,42,A4[0]-50,42)
        canvas.setFont('LabSans',8);canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(50,28,'EXERCISE 13 | '+('Preparation - results pending' if draft else 'Measured lab submission'))
        canvas.drawRightString(A4[0]-50,28,str(doc.page));canvas.restoreState()
    output.parent.mkdir(parents=True,exist_ok=True)
    SimpleDocTemplate(str(output),pagesize=A4,rightMargin=50,leftMargin=50,topMargin=43,bottomMargin=56,
                      title='Exercise 13 - '+('Preparation Report' if draft else 'Final Lab Report'),author=student.get('name','')).build(story,onFirstPage=footer,onLaterPages=footer)
    print('Report saved:',output)


def main():
    p=argparse.ArgumentParser();p.add_argument('--results',default='/results');p.add_argument('--draft',action='store_true')
    p.add_argument('--check-only',action='store_true');p.add_argument('--output');a=p.parse_args();root=Path(a.results)
    if a.check_only:
        validate(root);print('Required measured lab evidence is complete and passed.');return
    output=Path(a.output) if a.output else root/('Exercise_13_Preparation_Report.pdf' if a.draft else 'Exercise_13_Final_Report.pdf')
    build(root,output,a.draft)


if __name__=='__main__': main()
