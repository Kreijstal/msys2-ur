"""Build a deterministic shared source-export and consumer-validation workflow bundle."""
from pathlib import Path
import gzip,hashlib,io,sys,tarfile
here=Path(__file__).resolve().parent;output=Path(sys.argv[1]).resolve();names={'original-source-contracts.json','README.md','SDK.Microsoft.TemplateEngine.Cli.csproj','SDK.LICENSE.TXT'}
with output.open('wb') as stream,gzip.GzipFile(fileobj=stream,mode='wb',mtime=0,filename='') as compressed,tarfile.open(fileobj=compressed,mode='w') as t:
    for path in sorted((p for p in here.iterdir() if p.suffix in {'.py','.cs'} or p.name in names),key=lambda p:p.name):
        data=path.read_bytes();info=tarfile.TarInfo('wcwidth-source-workflow/'+path.name);info.mode=0o644;info.size=len(data);t.addfile(info,io.BytesIO(data))
print(hashlib.sha256(output.read_bytes()).hexdigest())
