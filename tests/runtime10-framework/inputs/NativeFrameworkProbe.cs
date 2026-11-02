using System;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
internal static class Program {
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int IcuLoad();
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int IcuVersion();
 static byte[] RoundTrip(byte[] input,Func<Stream,CompressionMode,Stream> create) {
  using var compressed=new MemoryStream();using(var encoder=create(compressed,CompressionMode.Compress))encoder.Write(input);
  using var data=new MemoryStream(compressed.ToArray());using var decoder=create(data,CompressionMode.Decompress);using var decoded=new MemoryStream();decoder.CopyTo(decoded);return decoded.ToArray();
 }
 static int Main(string[] args) {
  if(Environment.Version!=new Version(10,0,5))return 1;
  byte[] data=Encoding.UTF8.GetBytes(string.Concat(Enumerable.Repeat("source10 λ 😀 \0 gzip brotli zlib ",1000)));
  if(!data.SequenceEqual(RoundTrip(data,(s,m)=>new GZipStream(s,m,true))))return 2;
  if(!data.SequenceEqual(RoundTrip(data,(s,m)=>new DeflateStream(s,m,true))))return 3;
  if(!data.SequenceEqual(RoundTrip(data,(s,m)=>new BrotliStream(s,m,true))))return 4;
  using(var zip=new MemoryStream()) {
   using(var archive=new ZipArchive(zip,ZipArchiveMode.Create,true)){using var entry=archive.CreateEntry("λ/data.txt").Open();entry.Write(data);}
   zip.Position=0;using var reader=new ZipArchive(zip,ZipArchiveMode.Read);using var entryRead=reader.GetEntry("λ/data.txt")!.Open();using var output=new MemoryStream();entryRead.CopyTo(output);if(!data.SequenceEqual(output.ToArray()))return 5;
  }
  nint icu=NativeLibrary.Load(args[0]);var load=Marshal.GetDelegateForFunctionPointer<IcuLoad>(NativeLibrary.GetExport(icu,"GlobalizationNative_LoadICU"));if(load()!=1)return 6;
  var version=Marshal.GetDelegateForFunctionPointer<IcuVersion>(NativeLibrary.GetExport(icu,"GlobalizationNative_GetICUVersion"));if(version()==0)return 7;
  if(1.5.ToString("N1",CultureInfo.GetCultureInfo("de-DE"))!="1,5")return 8;
  if("i".ToUpper(CultureInfo.GetCultureInfo("tr-TR"))!="İ")return 9;
  if("e\u0301".Normalize(NormalizationForm.FormC)!="é")return 10;
  return 0;
 }
}
