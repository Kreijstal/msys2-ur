#!/usr/bin/env python3
"""Package DBeaver's upstream OSGi composites from local source-built JARs."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import zipfile


def manifest_headers(text):
    headers = {}
    key = None
    for line in text.replace('\r', '').splitlines():
        if line.startswith(' '):
            if key is None:
                raise ValueError('Manifest continuation without a header')
            headers[key] += line[1:]
        elif line:
            key, value = line.split(':', 1)
            if key in headers:
                raise ValueError('Duplicate manifest header: ' + key)
            headers[key] = value.lstrip()
    return headers


def manifest_bytes(headers):
    lines = []
    for key, value in headers.items():
        data = (key + ': ' + value).encode('utf-8')
        first = True
        while data:
            limit = 70 if first else 69
            end = min(limit, len(data))
            while end < len(data) and data[end] & 0xC0 == 0x80:
                end -= 1
            lines.append((b'' if first else b' ') + data[:end])
            data = data[end:]
            first = False
    return b'\r\n'.join(lines) + b'\r\n\r\n'


def main():
    config_path, name, source_path, inputs_path, output_path = sys.argv[1:]
    config = json.loads(Path(config_path).read_text())[name]
    files = []
    inventory = []
    used = set()
    for line in Path(inputs_path).read_text().splitlines():
        gav, jarpath = line.split('\t')
        if gav in config['excluded'] or gav.split(':')[0] + ':*' in config['excluded']:
            continue
        jar = Path(jarpath)
        entry = 'lib/' + jar.name
        if entry in used:
            raise ValueError('Duplicate nested JAR: ' + entry)
        used.add(entry)
        with zipfile.ZipFile(jar) as archive:
            if not any(n.endswith('.class') for n in archive.namelist()):
                raise ValueError('Dependency contains no rebuilt bytecode: ' + str(jar))
        files.append((entry, jar))
        inventory.append({'coordinate': gav, 'file': entry,
                          'sha256': hashlib.sha256(jar.read_bytes()).hexdigest()})
    if not files:
        raise ValueError('Composite contains no libraries')
    headers = {
        'Manifest-Version': '1.0',
        'Bundle-ManifestVersion': '2',
        'Bundle-SymbolicName': config['bsn'],
        'Bundle-Version': config['version'],
        'Bundle-Name': config['bsn'],
        'Bundle-Vendor': 'DBeaver Corp',
        'Bundle-ActivationPolicy': 'lazy',
        'Bundle-RequiredExecutionEnvironment': 'JavaSE-21',
        'Eclipse-BundleShape': 'dir',
        'Bundle-ClassPath': ','.join(entry for entry, _ in files),
        # OSGi requires imports for JRE namespaces outside java.* as well.
        'DynamicImport-Package': 'javax.*,org.w3c.*,org.xml.*,org.ietf.*',
    }
    headers.update(manifest_headers((Path(source_path) / config['manifest']).read_text()))
    if name == 'logback':
        # Equinox lets the SLF4J API discover this provider's SPI resources.
        headers['Eclipse-RegisterBuddy'] = 'slf4j.api'
    timestamp = time.gmtime(max(315532800, int(os.environ.get('SOURCE_DATE_EPOCH', '1787875200'))))[:6]
    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    target = output / (config['bsn'] + '_' + config['version'] + '.jar')
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        def write(entry, data):
            info = zipfile.ZipInfo(entry, timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
        write('META-INF/MANIFEST.MF', manifest_bytes(headers))
        write('META-INF/source-built-libraries.json', (json.dumps(inventory, indent=2) + '\n').encode())
        for entry, path in files:
            write(entry, path.read_bytes())
    with zipfile.ZipFile(target) as archive:
        assert manifest_headers(archive.read('META-INF/MANIFEST.MF').decode()) == headers
        assert all(entry in archive.namelist() for entry, _ in files)
    print(config['bsn'] + ': packaged ' + str(len(files)) + ' source-built JARs')


if __name__ == '__main__':
    main()
