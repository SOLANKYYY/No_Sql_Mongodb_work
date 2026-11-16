"""Python CLI entry point for the shared Lab 9.2 implementation.
Use Docker_Kit/run-partition.ps1 for the complete partition workflow.
"""
import runpy
from pathlib import Path
if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("lab9.py")), run_name="__main__")
