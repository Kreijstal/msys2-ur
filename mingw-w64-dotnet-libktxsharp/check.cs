using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using KtxSharp;
class Check {
static byte[] Level(int w,int h,int seed)=>Enumerable.Range(0,w*h*4).Select(i=>(byte)(i*7+seed)).ToArray();
// Hand-assembled KTX 1.1 file: RGBA8 4x4 with a full 3-level mip chain and one key/value pair.
static byte[] BuildKtx(bool bigEndian,List<byte[]> levels){
 var ms=new MemoryStream();
 void U32(uint v){var b=BitConverter.GetBytes(v);if(bigEndian)Array.Reverse(b);ms.Write(b);}
 ms.Write(new byte[]{0xAB,0x4B,0x54,0x58,0x20,0x31,0x31,0xBB,0x0D,0x0A,0x1A,0x0A});
 U32(0x04030201);
 var kv=Encoding.UTF8.GetBytes("KTXorientation\0S=r,T=d\0");int kvPad=(4-kv.Length%4)%4;
 foreach(var v in new uint[]{0x1401,1,0x1908,0x8058,0x1908,4,4,0,0,1,(uint)levels.Count,(uint)(4+kv.Length+kvPad)})U32(v);
 U32((uint)kv.Length);ms.Write(kv);ms.Write(new byte[kvPad]);
 foreach(var l in levels){U32((uint)l.Length);ms.Write(l);}
 return ms.ToArray();}
static void Verify(string what,KtxStructure k,List<byte[]> levels){
 var h=k.header;
 if(h.glDataType!=GlDataType.GL_UNSIGNED_BYTE||h.glTypeSizeAsUint!=1||h.glFormat!=GlPixelFormat.GL_RGBA||h.glInternalFormat!=GlInternalFormat.GL_RGBA8_OES||h.glPixelFormat!=GlPixelFormat.GL_RGBA)throw new Exception(what+" GL enums "+h);
 if(h.pixelWidth!=4||h.pixelHeight!=4||h.pixelDepth!=0||h.numberOfFaces!=1||h.numberOfMipmapLevels!=3)throw new Exception(what+" dimensions "+h);
 if(!h.metadataDictionary.TryGetValue("KTXorientation",out var o)||!o.isString||o.stringValue!="S=r,T=d")throw new Exception(what+" metadata");
 if(k.textureData.textureType!=TextureTypeBasic.Basic2DWithMipmaps)throw new Exception(what+" texture type "+k.textureData.textureType);
 var got=k.textureData.textureDataOfMipmapLevel;
 if(got.Count!=3||!got.Zip(levels,(a,b)=>a.SequenceEqual(b)).All(x=>x))throw new Exception(what+" mip payloads");}
static void Main(){
var asm=typeof(KtxLoader).Assembly.GetName();
if(asm.Name!="KtxSharp"||asm.Version!=new Version(0,9,2,0))throw new Exception("assembly identity "+asm.FullName);
var levels=new List<byte[]>{Level(4,4,1),Level(2,2,2),Level(1,1,3)};
foreach(var big in new[]{false,true}){
 var bytes=BuildKtx(big,levels);var what=big?"big-endian":"little-endian";
 var (ok,err)=KtxLoader.CheckIfInputIsValid(new MemoryStream(bytes));if(!ok)throw new Exception(what+" rejected: "+err);
 var k=KtxLoader.LoadInput(new MemoryStream(bytes));Verify(what,k,levels);
 if(k.header.isInputLittleEndian==big)throw new Exception(what+" endianness flag");
 // Writer round trip, both byte orders
 foreach(var mode in new[]{KtxWriter.OverrideEndianness.WriteLittleEndian,KtxWriter.OverrideEndianness.WriteBigEndian}){
  var outMs=new MemoryStream();KtxWriter.WriteTo(k,outMs,mode);
  var again=KtxLoader.LoadInput(new MemoryStream(outMs.ToArray()));Verify(what+" -> "+mode,again,levels);
  if(again.header.isInputLittleEndian!=(mode==KtxWriter.OverrideEndianness.WriteLittleEndian))throw new Exception("writer byte order "+mode);
  if(!big&&mode==KtxWriter.OverrideEndianness.WriteLittleEndian&&!outMs.ToArray().SequenceEqual(bytes))throw new Exception("little-endian rewrite is not byte identical");}}
// Creator API
var created=KtxCreator.Create(GlDataType.GL_UNSIGNED_BYTE,GlPixelFormat.GL_RGBA,GlInternalFormat.GL_RGBA8_OES,4,4,levels,new Dictionary<string,MetadataValue>{["KTXorientation"]=new MetadataValue(Encoding.UTF8.GetBytes("S=r,T=d\0"))});
var cms=new MemoryStream();KtxWriter.WriteTo(created,cms);Verify("KtxCreator",KtxLoader.LoadInput(new MemoryStream(cms.ToArray())),levels);
// Corrupt identifier must be rejected
var bad=BuildKtx(false,levels);bad[1]^=0xFF;if(KtxLoader.CheckIfInputIsValid(new MemoryStream(bad)).isValid)throw new Exception("accepted corrupt identifier");
Console.WriteLine("PASS LibKTX/KtxSharp "+asm.Version+"; hand-built KTX1 RGBA8 4x4 3-mip file parsed in both byte orders, metadata, writer round trips (byte-identical LE), KtxCreator, corrupt-identifier rejection");}}
