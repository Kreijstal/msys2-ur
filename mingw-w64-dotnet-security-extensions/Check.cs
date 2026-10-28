using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography.X509Certificates;
using System.Threading.Tasks;
using Microsoft.Security.Extensions;
class Program
{
 static void Require(bool value,string message){if(!value)throw new Exception(message);}
 static FileSignatureInfo Read(string path)
 {
  using var file=File.OpenRead(path);file.Position=Math.Min(7,file.Length);long before=file.Position;
  var info=FileSignatureInfo.GetFromFileStream(file);Require(file.Position==before,"Caller position changed");
  GC.Collect();GC.WaitForPendingFinalizers();return info;
 }
 static void Release(FileSignatureInfo value){value.SigningCertificate?.Dispose();value.TimestampCertificate?.Dispose();}
 [STAThread]
 static void Main(string[] args)
 {
  string root=args[0];
  var assembly=typeof(FileSignatureInfo).Assembly;
  Require(assembly.GetName().Version==new Version(10,0,0,0)&&Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()=="31bf3856ad364e35","Assembly identity");
  Require(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>().Version=="1.4.0.0","Source file version");
  Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion=="1.4.0-msys2-source-port+wintrust","Source identity");
  Require(Path.GetDirectoryName(assembly.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"Local consumer implementation");
  using var signer=new X509Certificate2(Path.Combine(root,"signer.cer"));using var tsa=new X509Certificate2(Path.Combine(root,"tsa.cer"));
  foreach(string name in new[]{"fixture.exe","signed.exe","timestamped.exe","tampered.exe","signed.ps1","unsigned.ps1"})
  {
   var info=Read(Path.Combine(root,name));
   Console.WriteLine(name+": "+info.State+" / "+info.StateReason+" / "+info.Kind+" OS="+info.IsOSBinary+" timestamp="+(info.TimestampCertificate!=null));
   if(name=="fixture.exe"||name=="unsigned.ps1")Require(info.State==SignatureState.Unsigned&&info.Kind==SignatureKind.None&&info.SigningCertificate==null,"Unsigned source fixture");
   else
   {
    Require(info.Kind==SignatureKind.Embedded&&info.SigningCertificate.Thumbprint==signer.Thumbprint&&!info.IsOSBinary,"Signer identity");
    if(name=="tampered.exe")Require(info.State==SignatureState.Invalid&&info.StateReason==SignatureStateReason.BadDigest,"Tampered content trusted");
    else Require(info.State==SignatureState.SignedAndNotTrusted&&info.StateReason==SignatureStateReason.UntrustedRoot,"Self-signed trust status");
    if(name=="timestamped.exe")Require(info.TimestampCertificate?.Thumbprint==tsa.Thumbprint,"Timestamp certificate identity/lifetime");
   }
   Release(info);
  }
  string windows=Environment.GetFolderPath(Environment.SpecialFolder.Windows);
  foreach(string path in new[]{Path.Combine(windows,"System32","kernel32.dll"),Path.Combine(windows,"System32","notepad.exe")})
  {
   var info=Read(path);Console.WriteLine(Path.GetFileName(path)+": "+info.State+" / "+info.Kind+" OS="+info.IsOSBinary);
   Require(info.State==SignatureState.SignedAndTrusted&&info.StateReason==SignatureStateReason.None&&info.IsOSBinary&&info.Kind==SignatureKind.Catalog&&info.SigningCertificate!=null,"Windows catalog signature/trust");Release(info);
  }
  Parallel.For(0,8,_=>{var value=Read(Path.Combine(root,"signed.exe"));Require(value.State==SignatureState.SignedAndNotTrusted,"Concurrent source query");Release(value);});
  using(var shared=File.OpenRead(Path.Combine(root,"signed.exe")))
  {
   shared.Position=9;
   Parallel.For(0,8,_=>{var info=FileSignatureInfo.GetFromFileStream(shared);Require(info.State==SignatureState.SignedAndNotTrusted,"Concurrent shared stream trust");Release(info);});
   Require(shared.Position==9,"Concurrent shared stream position");
  }
  string renamed=Path.Combine(root,"renamed-π.exe"),original=Path.Combine(root,"rename-source.exe");File.Copy(Path.Combine(root,"signed.exe"),original,true);
  using(var file=new FileStream(original,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))
  {
   File.Move(original,renamed,true);
   var info=FileSignatureInfo.GetFromFileStream(file);Require(info.Kind==SignatureKind.Embedded&&info.SigningCertificate.Thumbprint==signer.Thumbprint,"Open handle after rename");Release(info);
  }
  File.Delete(renamed);
  // A FileStream must authenticate its open handle even if its original path
  // is replaced by a different, trusted file while the handle stays open.
  string replaced=Path.Combine(root,"path-replaced.exe"),saved=Path.Combine(root,"original-handle.exe");
  File.Copy(Path.Combine(root,"fixture.exe"),replaced,true);
  using(var file=new FileStream(replaced,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))
  {
   File.Move(replaced,saved,true);
   File.Copy(Path.Combine(windows,"System32","notepad.exe"),replaced);
   var info=FileSignatureInfo.GetFromFileStream(file);
   Require(info.State==SignatureState.Unsigned&&info.Kind==SignatureKind.None&&info.SigningCertificate==null,"Trusted replacement path confused with unsigned open handle");Release(info);
  }
  File.Delete(replaced);File.Delete(saved);
  using(var originalFile=File.OpenRead(Path.Combine(root,"signed.exe")))
  using(var handleFile=new FileStream(originalFile.SafeFileHandle,FileAccess.Read))
  {
   var info=FileSignatureInfo.GetFromFileStream(handleFile);Require(info.Kind==SignatureKind.Embedded&&info.SigningCertificate.Thumbprint==signer.Thumbprint,"Handle-only FileStream");Release(info);
  }
  foreach(string name in new[]{"empty.txt","truncated.exe"})
  {
   using var file=File.OpenRead(Path.Combine(root,name));
   var info=FileSignatureInfo.GetFromFileStream(file);
   Require(info.State!=SignatureState.SignedAndTrusted,"Invalid/empty file trusted");Release(info);
  }
  using(var writeOnly=new FileStream(Path.Combine(root,"write-only.bin"),FileMode.Create,FileAccess.Write))
  {try{FileSignatureInfo.GetFromFileStream(writeOnly);throw new Exception("Write-only stream accepted");}catch(ArgumentException){}}
  var closed=File.OpenRead(Path.Combine(root,"fixture.exe"));closed.Dispose();
  try{FileSignatureInfo.GetFromFileStream(closed);throw new Exception("Closed stream accepted");}catch(ObjectDisposedException){}
  try{FileSignatureInfo.GetFromFileStream(null);throw new Exception("Null input accepted");}catch(ArgumentNullException){}
  using var process=System.Diagnostics.Process.GetCurrentProcess();
  for(int i=0;i<3;i++){var info=Read(Path.Combine(root,"timestamped.exe"));Release(info);}
  int handles=process.HandleCount;
  for(int i=0;i<24;i++){var info=Read(Path.Combine(root,"timestamped.exe"));Release(info);}
  GC.Collect();GC.WaitForPendingFinalizers();
  Require(process.HandleCount<=handles+4,"Signature query leaked kernel handles");
  var modules=process.Modules.Cast<System.Diagnostics.ProcessModule>().ToArray();
  Require(modules.Any(x=>x.ModuleName.Equals("msys-file-signature.dll",StringComparison.OrdinalIgnoreCase)),"Source native backend not loaded");
  Require(!modules.Any(x=>x.ModuleName.Equals("getfilesiginforedist.dll",StringComparison.OrdinalIgnoreCase)||x.FileName.Replace('\\','/').Contains("/Microsoft.NET/Framework",StringComparison.OrdinalIgnoreCase)),"Vendor/Framework implementation loaded");
  Console.WriteLine("PASS source identity, native unsigned/catalog/embedded/timestamp/corruption/trust results, certificate ownership, positions, concurrency, rename/handle streams and validation");
 }
}
