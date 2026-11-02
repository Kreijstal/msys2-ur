#!/usr/bin/env python3
# Copy the ReactOS headers that ovpn-dco-win trips over and fix them for the
# GCC build. Both fixes are pending in ReactOS (branch ovpn-dco-prereqs for
# wsk.h); drop each one once the ReactOS tree used here carries it.
import os, re, sys

ros, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

def fix(rel, func):
    src = open(os.path.join(ros, rel), encoding='utf-8', errors='replace').read()
    dst = func(src)
    if dst == src:
        print('%s: already fixed, not overlaid' % rel)
        return
    open(os.path.join(out, os.path.basename(rel)), 'w', encoding='utf-8').write(dst)
    print('%s: overlaid' % rel)

def wsk(s):
    # The NT 6.1 WskSendMessages types repeat the Windows 8 ones
    if '#if (NTDDI_VERSION < NTDDI_WIN8)\n/* Buffer list used by WskSendMessages' in s:
        return s
    m = re.search(r'\n(/\* Buffer list used by WskSendMessages.*?\n\s*_Inout_ PIRP Irp\);\n)', s, re.S)
    if not m:
        sys.exit('wsk.h: duplicate WskSendMessages block not found')
    return s.replace(m.group(1), '#if (NTDDI_VERSION < NTDDI_WIN8)\n' + m.group(1) + '#endif\n')

def netiodef(s):
    # Windows exposes the IPv6 version nibble as a bitfield
    old = 'typedef struct _IPV6_HEADER {\n  UINT32 VersionClassFlow;\n'
    if old not in s:
        return s
    return s.replace(old, '''typedef struct _IPV6_HEADER {
  union {
    UINT32 VersionClassFlow;
    struct {
      UINT32 : 4;
      UINT32 Version : 4;
      UINT32 : 24;
    };
  };
''')

fix('sdk/include/ddk/wsk.h', wsk)
fix('sdk/include/psdk/netiodef.h', netiodef)
