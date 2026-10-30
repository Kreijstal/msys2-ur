#!/usr/bin/env bash
set -euo pipefail
mkdir "${1:?usage: generate-fixtures.sh NEW_OUTPUT}"
cd "$1"
printf '%s\n' 'int main(void){return 42;}' > fixture.c
${MINGW_PREFIX}/bin/clang fixture.c -o fixture.exe
for kind in signer tsa;do
 usage=codeSigning;[[ $kind != tsa ]]||usage=critical,timeStamping
 MSYS2_ARG_CONV_EXCL='/CN=' ${MINGW_PREFIX}/bin/openssl req -x509 -newkey rsa:2048 -nodes -keyout "$kind.key" -out "$kind.crt" -days 2 -subj "/CN=MSYS2 source port test $kind" -addext "extendedKeyUsage=$usage" -addext keyUsage=digitalSignature > "$kind.log" 2>&1
 ${MINGW_PREFIX}/bin/openssl x509 -in "$kind.crt" -outform DER -out "$kind.cer"
done
${MINGW_PREFIX}/bin/osslsigncode sign -certs signer.crt -key signer.key -h sha256 -in fixture.exe -out signed.exe
${MINGW_PREFIX}/bin/osslsigncode sign -certs signer.crt -key signer.key -h sha256 -TSA-certs tsa.crt -TSA-key tsa.key -in fixture.exe -out timestamped.exe
printf '%s\n' 'Write-Output "owned source signature fixture"' > unsigned.ps1
${MINGW_PREFIX}/bin/osslsigncode sign -certs signer.crt -key signer.key -h sha256 -in unsigned.ps1 -out signed.ps1
/usr/bin/python3 - <<'PY'
from pathlib import Path
import struct
b=bytearray(Path('signed.exe').read_bytes());pe=struct.unpack_from('<I',b,0x3c)[0];optional=struct.unpack_from('<H',b,pe+20)[0];section=pe+24+optional
position=struct.unpack_from('<I',b,section+20)[0]+16;b[position]^=1;Path('tampered.exe').write_bytes(b)
Path('empty.txt').write_bytes(b'');Path('truncated.exe').write_bytes(b'MZ')
PY
