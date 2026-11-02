#!/usr/bin/env bash
set -euo pipefail
binary=$(cygpath -am "${1:?usage: check.sh BINARY NEW_OUTPUT}")
mkdir "${2:?missing output}";out=$(cd "$2" && pwd)
cd "$out"
printf '%s\n' 'int main(void){return 42;}' > fixture.c
/clang64/bin/clang fixture.c -o unsigned.exe
MSYS2_ARG_CONV_EXCL='/CN=' /clang64/bin/openssl req -x509 -newkey rsa:2048 -nodes -keyout signer.key -out signer.crt -days 2 -subj '/CN=MSYS2 source signing tool fixture' -addext extendedKeyUsage=codeSigning -addext keyUsage=digitalSignature > certificate.log 2>&1
"$binary" sign -certs signer.crt -key signer.key -h sha256 -in unsigned.exe -out signed.exe
"$binary" verify -CAfile signer.crt -in signed.exe
printf '%s\n' 'PASS source signing tool creates and verifies an owned PE Authenticode fixture; no trust-store changes'
