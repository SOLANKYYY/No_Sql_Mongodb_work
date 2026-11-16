"""Unified coursework CLI; all measured outputs come from actual runs."""
import argparse,os,shutil,sys,time,subprocess
from pathlib import Path
from core import *

def initialize():
    from pymongo.errors import OperationFailure
    with client('mongodb://mongo:27017/?directConnection=true') as c:
        try:c.admin.command('replSetGetStatus')
        except OperationFailure as e:
            if e.code!=94:raise
            c.admin.command('replSetInitiate',{'_id':'rs14','members':[{'_id':0,'host':'mongo:27017'}]})
        deadline=time.monotonic()+120
        while not c.admin.command('hello').get('isWritablePrimary'):
            if time.monotonic()>deadline:raise RuntimeError('MongoDB did not become primary.')
            time.sleep(1)
        c.exercise14.warmup.replace_one({'_id':'ready'},{'_id':'ready','message':'Exercise 14 local lab'},upsert=True)
        print('Dedicated MongoDB replica set ready: one PRIMARY. Secondary lag is N/A.',flush=True)

def export(destination):
    source=Path('/kit');dest=Path(destination);dest.mkdir(parents=True,exist_ok=True)
    for p in source.iterdir():
        if p.name in ('__pycache__',):continue
        if p.is_dir():shutil.copytree(p,dest/p.name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        else:shutil.copy2(p,dest/p.name)
    print('Published kit exported to the mounted destination.')

def run_unit_evidence():
    r=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd='/kit',capture_output=True,text=True)
    text=r.stdout+r.stderr;print(text,flush=True)
    save('lab14_unit_tests.json',{'timestamp':utc(),'passed':r.returncode==0,'kind':'mocked drivers and deterministic circuit-breaker tests; not live database evidence','output':text})
    if r.returncode:raise RuntimeError('Unit tests failed.')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['monitor', 'alert-test', 'lab14', 'schedule', 'wait-scheduler', 'init', 'unit-tests', 'validate', 'report', 'export'])
    p.add_argument('--samples',type=int,default=3);p.add_argument('--interval',type=int,default=30)
    p.add_argument('--external',action='store_true');p.add_argument('--destination',default='/work');p.add_argument('--output',default='/results');p.add_argument('--published',action='store_true')
    a=p.parse_args()
    if a.command=='monitor':
        from monitor import monitor
        monitor(a.samples,a.interval)
    elif a.command=='alert-test':
        from monitor import alert_test
        alert_test(a.external)
    elif a.command in ('lab14','schedule','wait-scheduler'):
        import backup
        {'lab14':backup.lab,'schedule':backup.schedule,'wait-scheduler':backup.wait_scheduler}[a.command]()
    elif a.command=='init':initialize()
    elif a.command=='export':export(a.destination)
    elif a.command=='unit-tests':run_unit_evidence()
    elif a.command in ('validate','report'):
        import report
        if a.command=='validate':report.validate(RESULTS,published=a.published);print('Required experiment evidence passed.')
        else:report.generate(RESULTS,Path(a.output))
if __name__=='__main__':
    try:main()
    except Exception as e:print(f'ERROR: {type(e).__name__}: {e}',file=sys.stderr);sys.exit(1)
