EXPERIMENT=18
import json, os, re
from pathlib import Path
from xml.sax.saxutils import escape
from common import ROOT, RESULTS, load, now
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.graphics.shapes import Drawing, Rect, String, Line

FONT=ROOT/'scripts/fonts'
for name,file in [('DejaVu','DejaVuSans.ttf'),('DejaVu-Bold','DejaVuSans-Bold.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT/file)))
pdfmetrics.registerFontFamily('DejaVu',normal='DejaVu',bold='DejaVu-Bold',italic='DejaVu',boldItalic='DejaVu-Bold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle('BodyX',fontName='DejaVu',fontSize=9,leading=14,spaceAfter=7))
styles.add(ParagraphStyle('SmallX',fontName='DejaVu',fontSize=7.3,leading=10,spaceAfter=4,wordWrap='CJK'))
styles.add(ParagraphStyle('HeadX',fontName='DejaVu-Bold',fontSize=13,leading=17,spaceBefore=12,spaceAfter=8,keepWithNext=True,textColor=colors.HexColor('#173E59')))
styles.add(ParagraphStyle('TitleX',fontName='DejaVu-Bold',fontSize=24,leading=29,spaceAfter=15,textColor=colors.HexColor('#173E59')))
def para(text,small=False):return Paragraph(escape(str(text)).replace('\n','<br/>'),styles['SmallX' if small else 'BodyX'])
def heading(text):return Paragraph(escape(text),styles['HeadX'])
def table(rows,widths=None):
    t=Table([[para(c,True) for c in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E5EFF4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),1,colors.HexColor('#26788A')),('GRID',(0,1),(-1,-1),0.25,colors.HexColor('#D6DEE4')),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    return t

def validate():
    e=load('evidence.json');state=load('run_state.json')
    if e.get('experiment')!=EXPERIMENT or e.get('passed') is not True or state.get('status')!='passed':raise ValueError('A successful current lab run is required')
    if EXPERIMENT==17:
        b=e['benchmark']
        if b['documents']!=5000 or b['queries']!=100 or b['dimensions']!=384 or len(e['rag'])<6 or e['rag'][-1]['history_exchanges_used']!=5:raise ValueError('Incomplete Exercise 17 evidence')
        if not b['rows'] or not b['mongodb_rows']:raise ValueError('Missing index measurements')
    else:
        if not 1000<=e['data']['selected']<=15000 or e['data']['sources']<2:raise ValueError('Incomplete dataset evidence')
        if any(len(v)!=10 or any(x!=1000 for x in v) for v in e['write_checks'].values()) or len(e['write_checks'])!=3:raise ValueError('Write persistence checks incomplete')
        if len(e['queries'])!=12 or any(x['runs']!=10 for x in e['queries']):raise ValueError('Need 4 workloads x 3 databases x 10 runs')
        if not all(x['matched_all_backends'] for x in e['checks'].values()):raise ValueError('Cross-engine correctness failed')
    print('Required measured experiment evidence passed.')
    return e

def publication():
    p=load('published.json')
    repo=r'[a-z0-9][a-z0-9_-]+/nosql-exercise'+str(EXPERIMENT)
    if not isinstance(p.get('digest'),str) or not re.fullmatch(repo+r'@sha256:[0-9a-f]{64}',p['digest']):raise ValueError('Invalid publication digest string')
    expected=p['digest'].split('@')[0]
    if p.get('docker_url')!='https://hub.docker.com/r/'+expected or p.get('image')!=expected+':exercise'+str(EXPERIMENT) or p.get('verified_pull') is not True:raise ValueError('Publication has not been verified')
    return p

def footer(canvas,doc):
    canvas.setStrokeColor(colors.HexColor('#26788A'));canvas.line(42,40,553,40)
    canvas.setFont('DejaVu',8);canvas.setFillColor(colors.HexColor('#526674'))
    canvas.drawString(42,27,f'Exercise {EXPERIMENT} | Solanki Om Narendra | 24BTRCL190')
    canvas.drawRightString(553,27,str(doc.page))

def architecture():
    d=Drawing(500,158)
    boxes=[(165,115,170,32,'Threat export / API'),(165,60,170,32,'Normalize actual record count'),(0,0,150,34,'MongoDB: event history'),(175,0,150,34,'Cassandra: query tables'),(350,0,150,34,'Neo4j: relationships')]
    for x,y,w,h,label in boxes:
        d.add(Rect(x,y,w,h,fillColor=colors.HexColor('#E5EFF4'),strokeColor=colors.HexColor('#26788A'),rx=4,ry=4))
        d.add(String(x+w/2,y+13,label,textAnchor='middle',fontName='DejaVu',fontSize=8))
    d.add(Line(250,115,250,92,strokeColor=colors.HexColor('#26788A')))
    for x in [75,250,425]:d.add(Line(250,60,x,34,strokeColor=colors.HexColor('#26788A')))
    return d

def add_md(story,path):
    for block in path.read_text().splitlines():
        block=block.strip()
        if not block:continue
        if block.startswith('#'):story.append(heading(block.lstrip('# ').strip()))
        else:story.append(para(block))

def build(path,e=None,p=None,guide=False):
    title='Vector Search and RAG Foundations' if EXPERIMENT==17 else 'Comparative Threat Intelligence Capstone'
    story=[para('NOSQL DATABASES USING MONGODB'),Paragraph(f'Exercise {EXPERIMENT}<br/>{escape(title)}',styles['TitleX'])]
    student=load('student.json') if (RESULTS/'student.json').exists() else {'name':'Solanki Om Narendra','roll':'24BTRCL190'}
    story += [para(student['name']+' | '+student['roll']),para('PREPARATION GUIDE - NOT A COMPLETED LAB REPORT' if guide else 'FINAL EXPERIMENT REPORT | generated '+now())]
    if guide:
        story += [heading('Status'),para('Code and run instructions are prepared. No live database measurements or successful Docker publication are claimed by this guide. Run the kit, capture actual screenshots, publish the image, and generate the final report.'),heading('Separate Docker repository'),para(f'Intended: https://hub.docker.com/r/solankyyy/nosql-exercise{EXPERIMENT}'),para('The intended link is not proof that an image has been uploaded.'),heading('Run sequence'),para('SETUP.ps1 -AllowSystemDrive -> RUN.ps1 -> PUBLISH.ps1 -> COLLECT.ps1 -> STOP.ps1'),para('Run one command at a time in the folder containing SETUP.ps1. Use README.md for full PowerShell commands. Keep Docker Desktop running. Do not proceed after a failed command.')]
        if EXPERIMENT==18:story += [heading('Required input'),para('This kit includes 15,000 public indicator observations from five source events and three publishers. The reduced workload is a user-requested departure from the original 100,000-record assignment. No synthetic padding is used. See data/README.md for source semantics.')]
        else:story += [heading('Local execution'),para('Real MiniLM embeddings, MongoDB Atlas Local vector search and FLAN-T5-small generation need model downloads on first run. Models are cached. No paid API key is required. HNSW vs IVF is a separate FAISS benchmark; see the methodology adaptation below.')]
    else:
        story += [heading('Verified Docker publication'),Paragraph('<link href="'+escape(p['docker_url'])+'" color="#176B84">'+escape(p['docker_url'])+'</link>',styles['BodyX']),para(p['image']),para(p['digest'],True),para('Push and subsequent pull succeeded. Publication recorded: '+p['timestamp']),heading('Environment'),para(json.dumps(e['environment'],indent=2),True)]
        if EXPERIMENT==17:
            story += [para('Deployment: '+e['deployment']),heading('Lab 17.1 - RAG pipeline'),para(f"{e['documents']} documents became {e['chunks']} chunks. Actual MongoDB retrieval and local model generation completed. Six turns were stored, and the final prompt used the previous five exchanges.")]
            for i,r in enumerate(e['rag']):
                story += [heading('Dialogue '+str(i+1)),para('Question: '+r['question']),para('Generated answer: '+r['answer']),para('History exchanges used: '+str(r['history_exchanges_used'])),table([['Retrieved source','Vector score']]+[[h['source'],f"{h['score']:.4f}"] for h in r['retrieved']],[390,110])]
            story += [heading('Lab 17.2 - FAISS index comparison'),para(e['benchmark']['scope']),table([['Index / parameters','Build (s)','Mean ms','Recall@20']]+[[r['index']+' '+', '.join(f'{k}={r[k]}' for k in ['M','efConstruction','efSearch','nlist','nprobe'] if k in r),f"{r['build_seconds']:.3f}",f"{r['mean_ms']:.3f}",f"{100*r['recall_at_20']:.2f}%"] for r in e['benchmark']['rows']],[265,75,75,85])]
            if (RESULTS/'latency_recall.png').exists():story.append(Image(str(RESULTS/'latency_recall.png'),width=480,height=360))
            story += [heading('MongoDB service measurements (separate)'),table([['numCandidates','Mean ms','Median ms','Recall@20']]+[[r['numCandidates'],f"{r['mean_ms']:.3f}",f"{r['median_ms']:.3f}",f"{100*r['recall_at_20']:.2f}%"] for r in e['benchmark']['mongodb_rows']],[125]*4)]
            eligible=[r for r in e['benchmark']['rows'] if r['recall_at_20']>=.95]
            if eligible:
                best=min(eligible,key=lambda r:r['mean_ms'])
                story += [heading('Measured recommendation'),para('Among measured FAISS configurations reaching 95% recall@20, the lowest mean latency was: '+json.dumps(best)+'. This result is local to this corpus/hardware. MongoDB network latency is not directly comparable to in-process FAISS.')]
            else:story += [heading('Measured recommendation'),para('No measured FAISS setting reached 95% recall@20. Increase the search budget or choose exact retrieval when recall matters; do not assume the fastest setting is adequate.')]
        else:
            story += [heading('Executive summary'),para(f"This reduced-workload study compares the same {e['data']['selected']:,} supplied records across three live database engines. The assignment requested 100,000; this run does not claim to meet that original volume. MongoDB is the default operational record store; Cassandra is evaluated for query-oriented ingestion and Neo4j for relationship investigations. The measured workload table below, together with correctness checks, informs the recommendation. Community candidates require analyst verification; graph density alone cannot prove a false positive."),heading('Data and provenance'),para(json.dumps(e['data'],indent=2),True),heading('System architecture'),architecture(),heading('Measured engine versions'),para(json.dumps(e['versions'])),heading('Query performance comparison'),table([['Backend','Workload','Median ms','Events/s']]+[[r['backend'],r['query'],f"{r['median_ms']:.3f}",f"{r['events_per_second']:.1f}" if 'events_per_second' in r else '-'] for r in e['queries']],[110,155,115,120]),para('Every row summarizes 10 actual runs. Raw samples, environment and correctness checks are retained in results/evidence.json.'),heading('Correctness'),para(json.dumps(e['checks'],indent=2),True),heading('Graph-based review'),para('Algorithm: '+e['graph']['algorithm']),para(f"Graph nodes: {e['graph']['nodes']}; edges: {e['graph']['edges']}; high-degree targets skipped: {e['graph']['skipped_high_degree_targets']}; candidate communities: {len(e['graph']['communities'])}."),para(e['graph']['interpretation'])]
            for g in e['graph']['communities'][:20]:story.append(para(json.dumps(g),True))
            story += [heading('Measured workload winners')]
            for q in ['history','spread','daily','ingest_1000']:
                winner=min([r for r in e['queries'] if r['query']==q],key=lambda r:r['median_ms'])
                story.append(para(f"{q}: {winner['backend']} had the lowest observed median ({winner['median_ms']:.3f} ms). This is configuration-specific, not a universal engine ranking."))
            story += [heading('Scalability assessment - estimates only'),para('No 1M, 10M or 100M run was performed. The disk estimates below use the disclosed 1 KiB/event scenario, query-copy/index factors, three physical copies and 30% free-space reserve. They are planning arithmetic, not measured storage or production sizing guarantees.')]
            sizing=[['Events','MongoDB GiB','Cassandra GiB','Neo4j GiB','Initial CPU/RAM load-test budget']]
            for count,budget in [(1000000,'4 vCPU / 8-16 GB per node'),(10000000,'8 vCPU / 16-32 GB per node'),(100000000,'16 vCPU / 32-64 GB per node; partition and load-test')]:
                sizing.append([f'{count:,}']+[f'{count*1024*factor*3/.7/2**30:.1f}' for factor in [2,6,4]]+[budget])
            story += [table(sizing,[75,85,90,80,170]),para('Node counts and final CPU/RAM must follow measured throughput, working-set size, replication and availability targets. Neo4j factors assume an appropriate production deployment; Community 5.26 in this lab is single-node.'),heading('Final recommendation'),para('Keep normalized event provenance and flexible operational records in MongoDB. Add Cassandra when sustained ingestion and predictable partition-key queries justify four copies and operational repair work. Add Neo4j when relationship investigations justify graph-maintenance cost. For each tested query, use the measured winners above as local evidence, and retest under matched durability and resources. A polyglot design adds synchronization, backup and skills costs; choose it only when those benefits are demonstrated.')]
    story.append(PageBreak());add_md(story,ROOT/'docs/METHODOLOGY.md')
    if not guide:
        screenshots=Path(os.getenv('SCREENSHOTS_DIR','/screenshots'))
        images=sorted(list(screenshots.glob('*.png'))+list(screenshots.glob('*.jpg'))+list(screenshots.glob('*.jpeg')))
        story.append(heading('Screenshot evidence'))
        if not images:story.append(para('No screenshots were supplied at report generation. Measured JSON is available; add actual screenshots and rerun REPORT.ps1 to include visual evidence.'))
        for image in images:
            w,h=ImageReader(str(image)).getSize();scale=min(500/w,620/h)
            story += [PageBreak(),heading(image.name),Image(str(image),width=w*scale,height=h*scale)]
    doc=SimpleDocTemplate(str(path),pagesize=(595.28,841.89),rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=53,title=f'Exercise {EXPERIMENT} '+('Preparation Guide' if guide else 'Final Report'),author=student['name'])
    doc.build(story,onFirstPage=footer,onLaterPages=footer)

def report():
    e=validate();p=publication();out=RESULTS/f'Exercise_{EXPERIMENT}_Final_Report.pdf'
    build(out,e,p)
    print('Report saved:',out)
