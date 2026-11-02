#!/usr/bin/env python3
# Fill in the placeholders of ovpn-dco.inf the way stampinf does for a
# driver shipped without the KMDF co-installer.
#   stampinf.py <in.inf> <out.inf> <arch> <kmdf-version> <driver-version> [MM/DD/YYYY]
import datetime, re, sys

src, dst, arch, kmdf, version = sys.argv[1:6]
date = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] else datetime.date.today().strftime('%m/%d/%Y')

text = open(src, encoding='utf-8-sig', newline='').read()
nl = '\r\n' if '\r\n' in text else '\n'
out = []
in_version = False
for line in text.split(nl):
    if in_version and (not line.strip() or line.lstrip().startswith('[')):
        # stampinf appends DriverVer to the end of [Version]
        out.append('DriverVer = %s,%s.0' % (date, version))
        in_version = False
    if 'KMDFCOINSTALLERVERSION' in line:
        # No co-installer: KMDF is part of the OS. stampinf leaves a
        # bare LF after the comment, kept for byte-identical output.
        out.append(';\n')
        continue
    out.append(line.replace('$ARCH$', arch).replace('$KMDFVERSION$', kmdf))
    if re.match(r'^\s*\[Version\]\s*$', line, re.I):
        in_version = True
open(dst, 'w', encoding='utf-8', newline='').write(nl.join(out))
