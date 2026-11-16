"""Produce a PDF, chart, and readable terminal transcript from actual JSON results."""
import hashlib
import json
import os
from pathlib import Path
import statistics
from urllib.parse import urlparse
from xml.sax.saxutils import escape
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties, findfont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

FILES=('lab_10_1_bank.json','lab_10_2_inventory.json','lab_10_3_durability.json')


def summary_rows(inventory):
    rows=[]
    for workers in (1,4,8,16):
        for mode in ('transaction','nontransaction'):
            trials=[r for r in inventory['benchmarks'] if r['workers']==workers and r['mode']==mode]
            if len(trials)!=3:raise ValueError('Expected three trials per mode/thread count')
            values=[r['successfulPerSecond'] for r in trials]
            rows.append({'workers':workers,'mode':mode,'median':statistics.median(values),'min':min(values),'max':max(values),
                         'success':sum(r['counts']['reserved'] for r in trials),'requests':sum(r['requests'] for r in trials),
                         'retries':sum(r['transactionRetries'] for r in trials)})
    return rows


def transcript(bank,inventory,durability,rows):
    out=['EXERCISE 10 - TRANSACTIONS, ATOMICITY, DURABILITY & JOURNALING',
         'Measured evidence (timestamps identify each actual run).',
         '\nLAB 10.1 - BANK TRANSFER', 'Recorded: '+bank['startedAt'],
         'Money uses integer paise; total must remain 150000 paise.']
    for r in bank['cases']:
        out += ['\n'+r['name']+': '+r['outcome'].upper()+f" | verified={r['verified']}",
                '  BEFORE: '+str(r['before']), '  AFTER:  '+str(r['after'])]
        if r['error']:out.append('  '+r['error'])
        for retry in r['retries']:out.append('  Retry: '+str(retry))
    out += ['Duplicate transfer ID leaves balances/history unchanged: '+str(bank['duplicateCheck']),
            'Total final balance: '+str(bank['totalBalance']),
            '\nLAB 10.2 - INVENTORY', 'Recorded: '+inventory['startedAt']]
    for r in inventory['scarcity']:
        out += [f"\n8 shoppers / 5 units | max retries={r['maxRetries']}"]
        out += [f"  Request {w['request']}: {w['outcome']} | retries={len(w['retries'])}" for w in r['outcomes']]
        out += ['  Counts: '+str(r['counts']), '  Final stock/orders/version: '+str(r['final']),
                '  Inventory/order invariant: '+str(r['consistent'])]
    out += ['\nORDER CREATION FAILURE AFTER STOCK DECREMENT']
    for r in inventory['failureComparison']:out.append(f"  {r['mode']}: before={r['before']} after={r['after']} unchanged={r['unchanged']}")
    out += ['\nTHROUGHPUT - 64 requests x 3 trials per configuration',
            f"{'Threads':>7} {'Mode':<16} {'Median /s':>10} {'Min /s':>10} {'Max /s':>10} {'Success/req':>13} {'Retries':>8}"]
    for r in rows:out.append(f"{r['workers']:>7} {r['mode']:<16} {r['median']:>10.2f} {r['min']:>10.2f} {r['max']:>10.2f} {str(r['success'])+'/'+str(r['requests']):>13} {r['retries']:>8}")
    out += ['\nDURABILITY / JOURNALING', 'Recorded: '+durability['startedAt'],
            'Commit write concern: majority + j:true', 'All three process IDs changed: '+str(durability.get('allProcessesRestarted', False)), 'Restart method: '+durability['restartMethod']]
    for r in durability['observations']:out.append('  '+r['host']+' both committed documents present: '+str(r['present']))
    out += [durability['limitation'], '\nVerification: bank='+str(bank['verified'])+' inventory='+str(inventory['verified'])+' durability='+str(durability['verified']),
            'Scarcity expected five reserved / three out of stock observed: '+str(inventory['expectedFiveReserved'])]
    return '\n'.join(out)+'\n'


def generate(folder, hub_url=None):
    folder=Path(folder)
    if hub_url:
        u=urlparse(hub_url)
        if u.scheme!='https' or u.netloc!='hub.docker.com' or not u.path.startswith('/r/') or len(u.path.strip('/').split('/'))!=3 or u.query or u.fragment:
            raise ValueError('Use https://hub.docker.com/r/USERNAME/REPOSITORY')
    data=[]
    for file in FILES:
        d=json.loads((folder/file).read_text())
        if d.get('format')!='exercise10-transactions' or d.get('version')!=1:raise ValueError('Unexpected result format')
        data.append(d)
    bank,inventory,durability=data;rows=summary_rows(inventory)
    text=transcript(bank,inventory,durability,rows)
    (folder/'faculty-results.txt').write_text(text,encoding='utf-8')
    print(text,flush=True)
    fig,ax=plt.subplots(figsize=(8.0,3.5),layout='constrained')
    for mode,label,color in [('transaction','Transaction','#185b91'),('nontransaction','Separate stock + order writes','#c47a24')]:
        series=[r for r in rows if r['mode']==mode]
        med=[r['median'] for r in series]
        ax.errorbar([r['workers'] for r in series],med,
                    yerr=[[r['median']-r['min'] for r in series],[r['max']-r['median'] for r in series]],
                    marker='o',capsize=4,label=label,color=color)
    ax.set(xlabel='Concurrent threads',ylabel='Successful reservations / second',xticks=[1,4,8,16],ylim=(0,None))
    ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.2);ax.legend(fontsize=9)
    fig.savefig(folder/'throughput.png',dpi=180);plt.close(fig)
    for font_name, weight, style in [('LabSans','normal','normal'),('LabSans-Bold','bold','normal'),('LabSans-Italic','normal','italic'),('LabSans-BoldItalic','bold','italic')]:
        pdfmetrics.registerFont(TTFont(font_name,findfont(FontProperties(family='DejaVu Sans',weight=weight,style=style))))
    pdfmetrics.registerFontFamily('LabSans',normal='LabSans',bold='LabSans-Bold',italic='LabSans-Italic',boldItalic='LabSans-BoldItalic')
    styles=getSampleStyleSheet()
    for style in styles.byName.values():
        if hasattr(style,'fontName'):style.fontName='LabSans-Bold' if 'Bold' in style.fontName else 'LabSans'
    styles.add(ParagraphStyle(name='SmallText',fontName='LabSans',fontSize=8.3,leading=11,textColor=colors.HexColor('#35465a')))
    styles['Normal'].fontSize=9.5;styles['Normal'].leading=14
    styles['Title'].textColor=colors.HexColor('#174c70');styles['Heading1'].textColor=colors.HexColor('#174c70')
    story=[]
    def para(s,sty='Normal'):return Paragraph(escape(str(s)).replace('\n','<br/>'),styles[sty])
    def add(s,sty='Normal'):story.extend([para(s,sty),Spacer(1,8)])
    def table(headers,values,widths):
        t=Table([[para(x,'SmallText') for x in headers]]+[[para(x,'SmallText') for x in row] for row in values],colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e4eef5')),('VALIGN',(0,0),(-1,-1),'TOP'),
                              ('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#9eafb9')),('BOTTOMPADDING',(0,0),(-1,-1),7),
                              ('TOPPADDING',(0,0),(-1,-1),7),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f7f9')])]))
        story.extend([t,Spacer(1,10)])
    label=os.getenv('REPORT_LABEL','Measured lab report')
    add('EXERCISE 10','Title');add('Transactions, Atomicity, Durability & Journaling','Heading1');add(label)
    add('Docker Hub URL: '+(hub_url or 'NOT PROVIDED - add after publishing your image.'))
    add('The URL is provided by the student. This report does not verify publication. Demonstrate using the pulled image.','SmallText')
    if not hub_url:add('DRAFT - regenerate after Docker Hub publication.','Heading2')
    if not all(d.get('verified') for d in data):add('INCOMPLETE - one or more verification checks failed.','Heading2')
    add('Implementation','Heading2')
    add('A separate three-node replica set supports bank transfers and inventory reservations. Each transaction uses a private session, snapshot reads, and a majority, journaled commit. Monetary balances use integer paise. Conditional balance/stock and version updates prevent unguarded decrements.')
    add('Retry policy','Heading2')
    add('TransientTransactionError retries the complete transaction with exponential delays of 0.1, 0.2, 0.4, 0.8 and 1.6 seconds. UnknownTransactionCommitResult retries only commit; an unresolved commit is reported as uncertain. Business rejections are not retried. Stable transfer/order IDs guard against duplicate operations.')
    table(['Experiment','Recorded start (UTC)','Verified'],[[d['activity'],d['startedAt'],str(d['verified'])] for d in data],[110,310,80])
    add('Run details: MongoDB '+bank['mongoVersion']+'. Results are measured in the environment that generated these files. No performance ordering is assumed.','SmallText')
    story.append(PageBreak())
    add('10.1 - Bank transfer and rollback','Heading1')
    table(['Scenario','Outcome','Before balances','After balances','Verified'],[
        [r['name'],r['outcome'],', '.join(str(a['balance']) for a in r['before']['accounts']),', '.join(str(a['balance']) for a in r['after']['accounts']),str(r['verified'])] for r in bank['cases']],[135,65,105,105,90])
    add('Balances above are paise, ordered ACC-001 then ACC-002. Aborted cases compare both complete account records and the history count. The deliberate mid-transfer exception proves that the debit is rolled back, rather than merely rejecting before any write.')
    retries=bank['cases'][-1]['retries']
    add('Write-conflict experiment: the first attempt reads a snapshot, then a competing write advances the source version. The server detects the stale write. Recorded retry events: '+str(retries),'SmallText')
    add('Final total: '+str(bank['totalBalance'])+' paise. Duplicate-operation check: '+str(bank['duplicateCheck']))
    add('10.2 - Eight shoppers, five units','Heading1')
    table(['Retry limit','Reserved','Out of stock','Other outcomes','Final stock / orders'],[
        [r['maxRetries'],r['counts']['reserved'],r['counts']['out_of_stock'],sum(v for k,v in r['counts'].items() if k not in ('reserved','out_of_stock')),str(r['final']['stock'])+' / '+str(r['final']['orders'])] for r in inventory['scarcity']],[75,75,85,105,160])
    add('A first-read barrier creates genuine contention. Each worker has its own session. Out-of-stock is a business rejection, not a reason to exhaust retries. Five reservations and three out-of-stock outcomes observed: '+str(inventory['expectedFiveReserved']))
    add('Atomicity when order creation fails','Heading2')
    table(['Mode','Stock before -> after','Orders after','State unchanged'],[[r['mode'],str(r['before']['stock'])+' -> '+str(r['after']['stock']),r['after']['orders'],str(r['unchanged'])] for r in inventory['failureComparison']],[135,145,100,120])
    add('Both versions deliberately throw after the stock decrement. The transaction can undo the decrement. The separate find_one_and_update/order insert has no multi-document rollback. This is a controlled failure demonstration.','SmallText')
    story.append(PageBreak())
    add('Concurrency throughput','Heading1')
    story.append(Image(str(folder/'throughput.png'),width=500,height=219))
    table(['Threads','Mode','Median /s','Range /s','Success / requests'],[
        [r['workers'],r['mode'],f"{r['median']:.2f}",f"{r['min']:.2f} - {r['max']:.2f}",f"{r['success']} / {r['requests']}"] for r in rows],[50,135,85,130,100])
    add('Method: 64 one-unit requests and 64 units of stock per trial; three trials for each thread count and mode. Throughput is successful reservations divided by wall time, including retries and executor startup. Error bars show the minimum and maximum. Both modes use majority + j:true. There is no artificial barrier in these trials.','SmallText')
    tx=[r for r in rows if r['mode']=='transaction'];best=max(tx,key=lambda r:r['median'])
    add(f"Observed transaction peak: {best['median']:.2f} successful reservations/second at {best['workers']} threads. The measured curve may rise, flatten, or fall; contention and retries affect it. These short local trials are illustrative, not a production capacity forecast.")
    story.append(PageBreak())
    add('Durability and journaling','Heading1')
    add(durability['restartMethod'])
    add('All three MongoDB process IDs changed: '+str(durability.get('allProcessesRestarted', False)))
    table(['Member','Ledger + audit preserved'],[[r['host'],str(r['present'])] for r in durability['observations']],[340,160])
    add('Before restart, one transaction commits a ledger document and an audit document with majority + j:true. After the unclean process restart and election, the verifier reads both documents on every member and checks their complete contents.')
    add(durability['limitation']+'. Atomicity and durability are distinct: abort tests demonstrate all-or-nothing changes; this restart check tests survival of committed data.','SmallText')
    add('Demonstration and submission','Heading2')
    add('Publish the image with the completed results, pull it on the demonstration machine, extract /kit, and run demo-published.ps1 with that exact image tag. Its Compose service uses the pulled image without rebuilding. Follow README.md for commands. The assignment footer says Lab-09; this project follows the Exercise-10 title and tasks.')
    add('Evidence files and SHA256','Heading2')
    for name in FILES:
        add(name+'\n'+hashlib.sha256((folder/name).read_bytes()).hexdigest(),'SmallText')
    add('References','Heading2')
    for url in ['https://github.com/sujeetjagtap/NoSQL-Databases-using-MongoDB/tree/main/chapter-10',
                'https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/transactions/',
                'https://www.mongodb.com/docs/manual/core/transactions-in-applications/']:
        add(url,'SmallText')
    pdf=folder/'Exercise_10_Report.pdf'
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont('LabSans',8);canvas.setFillColor(colors.HexColor('#617485'))
        canvas.drawString(47,27,'Exercise 10 | '+label);canvas.drawRightString(A4[0]-47,27,str(doc.page));canvas.restoreState()
    SimpleDocTemplate(str(pdf),pagesize=A4,rightMargin=47,leftMargin=47,topMargin=40,bottomMargin=44,
                      title='Exercise 10 - Transactions Lab',author='Student lab results').build(story,onFirstPage=footer,onLaterPages=footer)
    print('PDF:',pdf,'\nChart:',folder/'throughput.png',flush=True)
