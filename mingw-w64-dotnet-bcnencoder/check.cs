using System;
using System.IO;
using System.Linq;
using BCnEncoder.Decoder;
using BCnEncoder.Encoder;
using BCnEncoder.Shared;
using BCnEncoder.Shared.ImageFiles;
class Check {
const int W=64,H=64;
static byte[] Gradient(){var p=new byte[W*H*4];for(int y=0;y<H;y++)for(int x=0;x<W;x++){int i=(y*W+x)*4;p[i]=(byte)(x*4);p[i+1]=(byte)(y*4);p[i+2]=(byte)((x+y)*2);p[i+3]=(byte)(255-x*2-y);}return p;}
static (double mean,int max) Error(byte[] src,ColorRgba32[] got,bool alpha){
 double sum=0;int max=0,n=0;
 for(int i=0;i<got.Length;i++){var c=got[i];int[] d={c.r-src[i*4],c.g-src[i*4+1],c.b-src[i*4+2],alpha?c.a-src[i*4+3]:0};
  foreach(var e in d.Take(alpha?4:3)){sum+=Math.Abs(e);max=Math.Max(max,Math.Abs(e));n++;}}
 return (sum/n,max);}
static void Main(){
var asm=typeof(BcEncoder).Assembly.GetName();
if(asm.Name!="BCnEncoder"||asm.Version!=new Version(2,1,0,0))throw new Exception("assembly identity "+asm.FullName);
var hp=typeof(Microsoft.Toolkit.HighPerformance.Memory2D<byte>).Assembly.GetName();
if(hp.Version!=new Version(7,0,0,0))throw new Exception("HighPerformance dependency "+hp.FullName);
var src=Gradient();var dec=new BcDecoder();
foreach(var (fmt,blockBytes,alpha) in new[]{(CompressionFormat.Bc1,8,false),(CompressionFormat.Bc3,16,true)}){
 var enc=new BcEncoder(fmt);enc.OutputOptions.GenerateMipMaps=false;enc.OutputOptions.Quality=CompressionQuality.BestQuality;
 var raw=enc.EncodeToRawBytes(src,W,H,PixelFormat.Rgba32);
 if(raw.Length!=1||raw[0].Length!=W/4*H/4*blockBytes)throw new Exception(fmt+" encoded size "+raw[0].Length);
 var back=dec.DecodeRaw(raw[0],W,H,fmt);var (mean,max)=Error(src,back,alpha);
 Console.WriteLine($"  {fmt}: {raw[0].Length} bytes, mean |err| {mean:F2}, max |err| {max}");
 if(mean>4||max>24)throw new Exception(fmt+" round-trip error too large");
 // Through a KTX container with a full mip chain (exercises Memory2D-based resampling)
 enc.OutputOptions.GenerateMipMaps=true;var ktx=enc.EncodeToKtx(src,W,H,PixelFormat.Rgba32);
 var ms=new MemoryStream();ktx.Write(ms);ms.Position=0;var reread=KtxFile.Load(ms);
 if(reread.header.NumberOfMipmapLevels!=7)throw new Exception(fmt+" mip levels "+reread.header.NumberOfMipmapLevels);
 var top=dec.Decode(reread);var e2=Error(src,top,alpha);if(Math.Abs(e2.mean-mean)>1e-9)throw new Exception(fmt+" KTX top level differs from raw path");}
// Uniform colour must be (near-)exact in BC1
var flat=Enumerable.Repeat(new byte[]{200,100,50,255},W*H).SelectMany(x=>x).ToArray();
var e=new BcEncoder(CompressionFormat.Bc1);e.OutputOptions.GenerateMipMaps=false;
var f=dec.DecodeRaw(e.EncodeToRawBytes(flat,W,H,PixelFormat.Rgba32)[0],W,H,CompressionFormat.Bc1);
if(f.Any(c=>Math.Abs(c.r-200)>4||Math.Abs(c.g-100)>2||Math.Abs(c.b-50)>4))throw new Exception("BC1 flat colour");
Console.WriteLine("PASS BCnEncoder.Net "+asm.Version+" (Microsoft.Toolkit.HighPerformance "+hp.Version+"); BC1/BC3 encode+decode of a 64x64 RGBA gradient within error bounds, KTX container with 7 mips round trip, BC1 flat colour");}}
