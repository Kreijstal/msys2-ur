"""Run all four original method bodies with a standalone ordinal string assertion."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

source,output=(Path(p).resolve() for p in sys.argv[1:])
output.mkdir()
original=(source/'test/BasicTests.cs').read_bytes()
text=original.decode('utf-8-sig').replace('\r\n','\n')
assert text.count('using Xunit;')==1 and text.count('[Fact]')==4 and text.count('Assert.Equal(')==4
text=text.replace('using Xunit;','').replace('[Fact]','').replace('Assert.Equal(','OwnedFixture.Equal(')
target=output/'BasicTests.cs';target.write_text(text)
shutil.copyfile(source/'test/TestConsole.cs',output/'TestConsole.cs')
(output/'test-overlay.json').write_text(json.dumps(dict(original_basic_tests_sha256=hashlib.sha256(original).hexdigest(),
    staged_basic_tests_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),original_test_console_sha256=hashlib.sha256((source/'test/TestConsole.cs').read_bytes()).hexdigest(),
    change='Remove four xUnit discovery attributes/using; substitute four string-equality assertion calls with owned ordinal string equality. All four method bodies, input keys and expected console output retained.'),indent=2)+'\n')
print('Staged all four original Pager rendering/scrolling cases and unchanged original TestConsole')
