# Writes a small MGCB content project for check(): texture, sprite font,
# a stock effect, a custom effect, an OBJ model and XML content.
import shutil, struct, sys, zlib
from pathlib import Path
out=Path(sys.argv[1]); font=Path(sys.argv[2]); resources=Path(sys.argv[3]); custom=Path(sys.argv[4])
out.mkdir(parents=True,exist_ok=True)
def png(path,w,h):
    raw=b''.join(b'\0'+b''.join(bytes((x*255//(w-1),y*255//(h-1),128,255)) for x in range(w)) for y in range(h))
    chunk=lambda t,d: struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
png(out/'texture.png',64,32)
shutil.copy(font,out/'Roboto-Bold.ttf')
(out/'font.spritefont').write_text('''<?xml version="1.0" encoding="utf-8"?>
<XnaContent xmlns:Graphics="Microsoft.Xna.Framework.Content.Pipeline.Graphics">
  <Asset Type="Graphics:FontDescription">
    <FontName>Roboto-Bold.ttf</FontName><Size>14</Size><Spacing>0</Spacing><UseKerning>true</UseKerning><Style>Regular</Style>
    <CharacterRegions><CharacterRegion><Start>&#32;</Start><End>&#126;</End></CharacterRegion></CharacterRegions>
  </Asset>
</XnaContent>
''')
for f in resources.glob('*.fxh'): shutil.copy(f,out/f.name)
shutil.copy(resources/'BasicEffect.fx',out/'basic.fx')
shutil.copy(custom,out/'custom.fx')
(out/'model.obj').write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 0 1\nvn 0 0 1\nf 1/1/1 2/2/1 3/3/1\n')
(out/'data.xml').write_text('<?xml version="1.0" encoding="utf-8"?>\n<XnaContent><Asset Type="System.String[]"><Item>MonoGame</Item><Item>MSYS2</Item></Asset></XnaContent>\n')
items=[('texture.png','TextureImporter','TextureProcessor'),('font.spritefont','FontDescriptionImporter','FontDescriptionProcessor'),
       ('basic.fx','EffectImporter','EffectProcessor'),('custom.fx','EffectImporter','EffectProcessor'),
       ('model.obj','OpenAssetImporter','ModelProcessor'),('data.xml','XmlImporter','PassThroughProcessor')]
text='/platform:DesktopGL\n/profile:HiDef\n/compress:False\n\n'
for name,imp,proc in items:
    text+=f'#begin {name}\n/importer:{imp}\n/processor:{proc}\n/build:{name}\n\n'
(out/'Content.mgcb').write_text(text)
print('wrote content project with',len(items),'items to',out)
