import argparse, sys, traceback, unittest
from common import ROOT

def main():
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['test','run','validate','report','prepare','ask'])
    p.add_argument('--question',default='How can analysts reduce false positives?')
    a=p.parse_args()
    if a.command=='test':
        suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
        if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful(): raise SystemExit(1)
    elif a.command in ('validate','report'):
        from report import validate, report
        validate()
        if a.command=='report': report()
    else:
        import lab
        if a.command=='ask': lab.ask(a.question)
        elif a.command=='prepare': lab.prepare()
        else: lab.run()
if __name__=='__main__':
    try: main()
    except Exception as e:
        print('FAILED:',type(e).__name__,str(e),file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
