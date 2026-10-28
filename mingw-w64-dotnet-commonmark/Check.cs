using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading.Tasks;
using CommonMark;
using CommonMark.Syntax;
class Program
{
 static void Require(bool value,string message){if(!value)throw new Exception(message);}
 static void Main()
 {
  var assembly=typeof(CommonMarkConverter).Assembly;
  Require(assembly.GetName().Version==new Version(0,1,0,0)&&Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()=="001ef8810438905d","Published assembly identity");
  Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion=="0.15.1+6f0ed9805065ee368c01fe931ca7d589e9341f11","Source provenance");
  Require(Path.GetRelativePath(AppContext.BaseDirectory,assembly.Location)=="CommonMark.dll","Consumer implementation location");
  Require(CommonMarkConverter.Version==new Version(0,15,1),"Package version from source nuspec");assembly.GetExportedTypes();
  var methods=typeof(CommonMark.Tests.Specification.Specs).GetMethods().Where(m=>m.GetCustomAttributes<Microsoft.VisualStudio.TestTools.UnitTesting.TestMethodAttribute>().Any()).ToArray();Require(methods.Length==622,"Entire upstream specification corpus");
  TextWriter console=Console.Out;
  try
  {
   Console.SetOut(TextWriter.Null);var specs=new CommonMark.Tests.Specification.Specs();
   foreach(var method in methods){try{method.Invoke(specs,null);}catch(TargetInvocationException error){throw new Exception("Upstream specification: "+method.Name,error.InnerException);}}
  }
  finally{Console.SetOut(console);}
  Console.WriteLine("PASS all 622 upstream CommonMark 0.26 specification cases, both HTML formatter paths and upstream source-position invariant");
  string text="π before\n\n## heading\n\n- **item**\n";var settings=CommonMarkSettings.Default.Clone();settings.TrackSourcePosition=true;
  var ast=CommonMarkConverter.Parse(text,settings);var heading=ast.AsEnumerable().First(e=>e.Block?.Tag==BlockTag.AtxHeading).Block;
  Require(text.Substring(heading.SourcePosition,heading.SourceLength)=="## heading\n","AST source positions");
  Require(ast.AsEnumerable().Any(e=>e.Inline?.Tag==InlineTag.Strong),"AST inline nodes used by documentation code fixes");
  settings=CommonMarkSettings.Default.Clone();settings.RenderSoftLineBreaksAsLineBreaks=true;Require(CommonMarkConverter.Convert("a\nb",settings).Replace("\r","")=="<p>a<br />\nb</p>\n","Cloned soft-break option");
  settings=CommonMarkSettings.Default.Clone();settings.UriResolver=uri=>"https://owned.invalid/"+uri;Require(CommonMarkConverter.Convert("[link](path)",settings).Contains("https://owned.invalid/path"),"URI resolver delegate");
  using var reader=new StringReader("**stream** π");using var writer=new StringWriter();CommonMarkConverter.Convert(reader,writer);Require(writer.ToString().Replace("\r","")=="<p><strong>stream</strong> π</p>\n","Streaming conversion");
  Parallel.For(0,12,_=>Require(CommonMarkConverter.Convert("**parallel**").Replace("\r","")=="<p><strong>parallel</strong></p>\n","Concurrent conversions"));
  Require(CommonMarkConverter.Convert((string)null)==null,"String overload null contract");
  try{CommonMarkConverter.Parse((TextReader)null);throw new Exception("Null reader accepted");}catch(ArgumentNullException){}
  foreach(System.Diagnostics.ProcessModule module in System.Diagnostics.Process.GetCurrentProcess().Modules)Require(!module.FileName.Replace('\\','/').Contains("/Microsoft.NET/Framework",StringComparison.OrdinalIgnoreCase),"Framework module loaded");
  Console.WriteLine("PASS source identity/types, source nuspec version, AST/Unicode positions, cloned settings, URI resolver, streaming, concurrency and validation");
 }
}
