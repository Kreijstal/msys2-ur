#!/usr/bin/env python3
"""Include upstream namespace support when selecting individual projected types."""
from pathlib import Path
import sys
native = Path(sys.argv[1])
for directory in sorted((native/'generator/strings/additions').iterdir()):
    target = native/'projection'/(directory.name+'.cs')
    if target.exists():
        with target.open('a') as output:
            for source in sorted(directory.glob('*.cs')):
                output.write('\n'+source.read_text(encoding='utf-8-sig'))
