"""Activity entry point. Full implementation is in ../Docker_Kit.
Run run.ps1 for the configured Docker environment; host Python alone has no replica-set DNS.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Docker_Kit'))
from lab10 import inventory
if __name__ == '__main__':
    inventory()
