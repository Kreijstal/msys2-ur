#!/usr/bin/env python3
# Build delay-load import libraries for wintun.dll with GNU dlltool.
#
# The VS project delay-loads its system libraries (DelayLoadDLLs). GNU ld
# cannot delay-load through an ordinary import library, so for every DLL
# this writes a .def file with the functions the objects actually import
# from it (found in the toolchain's lib<dll>.a) and turns it into a delay
# import library with dlltool --output-delaylib.
#
#   mkdelaylib.py --dlltool T --nm T --cc T --out DIR [--def name=file.def]
#                 --dlls dll... --objects a.obj...
import argparse, os, re, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument('--dlltool', required=True)
ap.add_argument('--nm', required=True)
ap.add_argument('--cc', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--def', dest='defs', action='append', default=[])
ap.add_argument('--dlls', nargs='+', required=True)
ap.add_argument('--objects', nargs='+', required=True)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

def nm(path, *flags):
    return subprocess.run([a.nm, *flags, path], check=True, capture_output=True, text=True).stdout

# Functions the objects call: __imp_<name> for dllimport declarations,
# plain <name> through the import thunk for the others
wanted = set()
for obj in a.objects:
    for line in nm(obj, '-u').splitlines():
        m = re.match(r'^\s*U (?:__imp_)?(\S+)$', line)
        if m:
            wanted.add(m.group(1))

def write_lib(dll, names):
    deffile = os.path.join(a.out, '%s.def' % dll)
    with open(deffile, 'w', newline='\n') as f:
        f.write('LIBRARY %s.dll\nEXPORTS\n' % dll)
        for n in sorted(names):
            f.write('\t%s\n' % n)
    subprocess.run([a.dlltool, '--input-def', deffile, '--dllname', '%s.dll' % dll,
                    '--output-delaylib', os.path.join(a.out, 'lib%s.delay.a' % dll)], check=True)
    print('lib%s.delay.a: %s' % (dll, ' '.join(sorted(names))))

taken = set()
for spec in a.defs:
    dll, deffile = spec.split('=', 1)
    names = set()
    for line in open(deffile):
        line = line.strip()
        if line and not re.match(r'^(LIBRARY|EXPORTS)\b', line, re.I):
            names.add(line.split()[0])
    write_lib(dll, names)
    taken |= names

for dll in a.dlls:
    implib = subprocess.run([a.cc, '-print-file-name=lib%s.a' % dll], check=True,
                            capture_output=True, text=True).stdout.strip()
    if not os.path.isabs(implib) or not os.path.exists(implib):
        sys.exit('lib%s.a not found' % dll)
    exported = set()
    for line in nm(implib).splitlines():
        m = re.match(r'^[0-9a-fA-F]+ I __imp_(\S+)$', line)
        if m:
            exported.add(m.group(1))
    names = (wanted & exported) - taken
    taken |= names
    write_lib(dll, names)
