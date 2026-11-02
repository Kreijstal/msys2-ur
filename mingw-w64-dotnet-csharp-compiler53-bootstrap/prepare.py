"""Prepare the complete original source and compiler-generation/evaluation tools."""
from pathlib import Path
import subprocess,sys
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();here=Path(__file__).resolve().parent
subprocess.run(['/usr/bin/python3',str(here/'legacy/prepare.py'),str(root),str(out)],check=True)
subprocess.run(['bash',str(here/'build-generators.sh'),str(out)],check=True)
subprocess.run(['/usr/bin/python3',str(here/'evaluate-net10-toolset.py'),str(out),str(root/'net10-evaluation'),str(root/'net10-plan')],check=True)
