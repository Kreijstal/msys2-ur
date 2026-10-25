#!/usr/bin/env python3
# Fill in wintun.inf the way the WDK's stampinf does and write the
# wintun-inf.h that upstream's extract-driverver.js derives from it.
#   stampinf.py <in.inf> <out.inf> <out.h> <arch> <version> <MM/DD/YYYY>
# This build has no signed catalog, so the CatalogFile line is dropped:
# the driver package is plainly unsigned instead of naming a missing file.
import datetime, re, sys

src, dst, hdr, arch, version, date = sys.argv[1:7]
ver = (version.split('.') + ['0', '0', '0'])[:4]
version = '.'.join(ver)

text = open(src, encoding='utf-8-sig', newline='').read()
nl = '\r\n' if '\r\n' in text else '\n'
out = []
in_version = False
for line in text.split(nl):
    if in_version and (not line.strip() or line.lstrip().startswith('[')):
        # stampinf appends DriverVer to the end of [Version]
        out.append('DriverVer = %s,%s' % (date, version))
        in_version = False
    if re.match(r'^\s*CatalogFile', line, re.I):
        continue
    out.append(line.replace('$ARCH$', arch))
    if re.match(r'^\s*\[Version\]\s*$', line, re.I):
        in_version = True
open(dst, 'w', encoding='utf-8', newline='').write(nl.join(out))

# FILETIME of midnight UTC on the DriverVer date, as extract-driverver.js has it
m, d, y = (int(x) for x in date.split('/'))
ms = int((datetime.datetime(y, m, d, tzinfo=datetime.timezone.utc) -
          datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)).total_seconds()) * 1000
with open(hdr, 'w', newline='\n') as f:
    f.write('#define WINTUN_INF_FILETIME { (DWORD)((%d0000ULL + 116444736000000000ULL) & 0xffffffffU), '
            '(DWORD)((%d0000ULL + 116444736000000000ULL) >> 32) }\n' % (ms, ms))
    f.write('#define WINTUN_INF_VERSION ((%sULL << 48) | (%sULL << 32) | (%sULL << 16) | (%sULL << 0))\n' % tuple(ver))
