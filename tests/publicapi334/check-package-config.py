"""Compare regenerated package policy assets with original release text metadata."""
from pathlib import Path
import hashlib
import json
import sys
import zipfile

config, published, output = (Path(p).resolve() for p in sys.argv[1:])
sha = lambda data: hashlib.sha256(data).hexdigest()
assert sha(published.read_bytes()) == '5a61b7ae142ccabf2e47ad89e0c75f27d6fd2f1eda12ee802fd9cd4acd157611'
records = {}
with zipfile.ZipFile(published) as original:
    for folder, package_path in [('rulesets','rulesets'),('editorconfig','editorconfig'),('globalconfig','buildTransitive/config'),('build','buildTransitive'),('documentation','documentation')]:
        for path in sorted((config / folder).rglob('*')):
            if not path.is_file():continue
            member = package_path + '/' + path.relative_to(config / folder).as_posix()
            expected = original.read(member)
            actual = path.read_bytes()
            records[member] = dict(expected_sha256=sha(expected), actual_sha256=sha(actual), bytes_equal=expected==actual, normalized_text_equal=expected.decode('utf-8-sig').replace('\r\n','\n')==actual.decode('utf-8-sig').replace('\r\n','\n'))
output.write_text(json.dumps(dict(files=records, all_text_metadata_equal=all(r['normalized_text_equal'] for r in records.values()), published_text_metadata_only=True, full_dependency_goal_complete=False), indent=2)+'\n')
print('Generated',len(records),'files; text differences:',[n for n,r in records.items() if not r['normalized_text_equal']])
assert all(r['normalized_text_equal'] for r in records.values())
