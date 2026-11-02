#!/usr/bin/env python3
"""Fetch the generated source bundles a recipe needs, verifying every SHA256."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import tempfile
import urllib.parse
import urllib.request

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('manifest',type=Path)
parser.add_argument('--root',type=Path,default=Path.cwd())
parser.add_argument('--release-base-url',help='HTTPS release download URL, including its tag')
parser.add_argument('--check-existing',action='store_true',help='Verify local bundles without downloading')
args=parser.parse_args();root=args.root.resolve();manifest=json.loads(args.manifest.read_text());assert manifest['format']==1
if not args.check_existing and (not args.release_base_url or urllib.parse.urlparse(args.release_base_url).scheme!='https'):
    parser.error('Provide an HTTPS --release-base-url, or use --check-existing')
checked=downloaded=0
for row in manifest['archives']:
    recipe=Path(row['recipe']);filename=Path(row['filename'])
    if recipe.is_absolute() or '..' in recipe.parts or len(filename.parts)!=1 or row['release_asset']!=Path(row['release_asset']).name:
        raise ValueError('Unsafe source manifest path')
    destination=(root/recipe/filename).resolve()
    if not destination.is_relative_to(root):raise ValueError('Source destination escapes repository')
    def matches(path):
        if not path.is_file() or path.stat().st_size!=row['bytes']:return False
        with path.open('rb') as source:return hashlib.file_digest(source,'sha256').hexdigest()==row['sha256']
    if matches(destination):checked+=1;continue
    if args.check_existing:raise ValueError('Missing or mismatched source bundle: '+str(destination))
    destination.parent.mkdir(parents=True,exist_ok=True)
    handle,name=tempfile.mkstemp(prefix='.source-download-',dir=destination.parent);os.close(handle);temporary=Path(name)
    try:
        url=args.release_base_url.rstrip('/')+'/'+urllib.parse.quote(row['release_asset'])
        with urllib.request.urlopen(url,timeout=120) as response,temporary.open('wb') as output:
            while chunk:=response.read(1024*1024):output.write(chunk)
        if not matches(temporary):raise ValueError('Source SHA256/size mismatch: '+row['release_asset'])
        temporary.replace(destination);downloaded+=1
    finally:
        temporary.unlink(missing_ok=True)
print(f'PASS {checked} existing bundles verified; {downloaded} downloaded and verified')
