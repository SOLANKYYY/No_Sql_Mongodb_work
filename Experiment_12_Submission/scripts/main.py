import sys,argparse,unittest,traceback
from common import ROOT,save,now

def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['test','prepare','bootstrap','register','run','validate','report','guide']);a=p.parse_args()
 if a.command=='test':
  result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
  if not result.wasSuccessful():raise SystemExit(1)
 elif a.command in ('validate','report','guide'):
  import report
  getattr(report,a.command)()
 else:
  import lab
  if a.command=='run':
   save('run_state.json',{'status':'running','at':now()})
   try:lab.run()
   except Exception:
    save('run_state.json',{'status':'failed','at':now()});raise
  else:getattr(lab,a.command)()
if __name__=='__main__':
 try:main()
 except Exception as e:
  print('FAILED:',type(e).__name__,str(e),file=sys.stderr);traceback.print_exc();sys.exit(1)
