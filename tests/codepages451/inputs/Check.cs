using System;
using System.Collections;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Text.Json;
using Mono.Cecil;
sealed class OwnedContext:AssemblyLoadContext
{
 readonly string folder;
 public OwnedContext(string folder):base(isCollectible:true){this.folder=folder;}
 protected override Assembly? Load(AssemblyName n)
 {
  bool own=(n.Name=="System.Text.Encoding.CodePages" && (n.Version==new Version(4,0,2,0) || n.Version==new Version(4,1,1,0))) || (n.Name=="System.Runtime.CompilerServices.Unsafe" && n.Version==new Version(4,0,4,1));
  return own?LoadFromAssemblyPath(Path.Combine(folder,n.Name+".dll")):null;
 }
}
static class Program
{
 static void Need(bool value,string label){if(!value)throw new Exception(label);}
 static void Main(string[] args)
 {
  string file=Path.GetFullPath(args[0]);using var meta=JsonDocument.Parse(File.ReadAllText(args[1]));var expected=meta.RootElement.GetProperty("System.Text.Encoding.CodePages.dll");var wanted=expected.GetProperty("api").EnumerateArray().Select(x=>x.GetString()!).ToArray();var actual=Api.Read(file);
  File.WriteAllLines(file+".missing-api.txt",wanted.Except(actual));File.WriteAllLines(file+".extra-api.txt",actual.Except(wanted));Need(wanted.SequenceEqual(actual),"All original public API entries");
  using var policy=JsonDocument.Parse(File.ReadAllText(args[2]));var rule=policy.RootElement.GetProperty(args[3]);
  using(var a=AssemblyDefinition.ReadAssembly(file))
  {
   Need(a.Name.FullName==expected.GetProperty("identity").GetString(),"Original identity");
   var refs=a.MainModule.AssemblyReferences.Select(r=>r.FullName).OrderBy(x=>x,StringComparer.Ordinal).ToArray();var original=expected.GetProperty("references").EnumerateArray().Select(x=>x.GetString()!).OrderBy(x=>x,StringComparer.Ordinal).ToArray();File.WriteAllLines(file+".actual-references.txt",refs);Need(refs.SequenceEqual(original),"Original dependency identities");
   Need(!a.CustomAttributes.Any(x=>x.AttributeType.FullName=="System.Runtime.CompilerServices.ReferenceAssemblyAttribute" || x.AttributeType.FullName=="System.Runtime.Versioning.TargetFrameworkAttribute"),"Original implementation/no-TFM-marker policy");
   foreach(var attr in expected.GetProperty("attributes").EnumerateArray())
   {
    string name=attr.GetProperty("type").GetString()!;if(!name.StartsWith("System.Reflection.",StringComparison.Ordinal) && name!="System.CLSCompliantAttribute" && name!="System.Resources.NeutralResourcesLanguageAttribute" && name!="System.Security.AllowPartiallyTrustedCallersAttribute" && name!="System.Runtime.InteropServices.DefaultDllImportSearchPathsAttribute")continue;
    var values=attr.GetProperty("arguments").EnumerateArray().Select(x=>x.GetString()).ToArray();Need(a.CustomAttributes.Any(x=>x.AttributeType.FullName==name && x.ConstructorArguments.Select(v=>Convert.ToString(v.Value,CultureInfo.InvariantCulture)).SequenceEqual(values)),"Original managed attribute "+name);
   }
   Need(a.MainModule.Resources.Count==rule.GetProperty("resources").EnumerateObject().Count(),"Original resource count");
   foreach(var r in rule.GetProperty("resources").EnumerateObject())
   {
    var resource=a.MainModule.Resources.OfType<EmbeddedResource>().Single(x=>x.Name==r.Name);
    if(r.Value.TryGetProperty("strings",out var strings))
    {
     using var reader=new ResourceReader(resource.GetResourceStream());var values=reader.Cast<DictionaryEntry>().ToDictionary(x=>(string)x.Key,x=>(string)x.Value!);Need(values.Count==strings.EnumerateObject().Count(),"Original resource string count");foreach(var x in strings.EnumerateObject())Need(values[x.Name]==x.Value.GetString(),"Original resource string "+x.Name);
    }
    else Need(Convert.ToHexString(SHA256.HashData(resource.GetResourceData())).ToLowerInvariant()==r.Value.GetProperty("sha256").GetString(),"Exact original binary resource "+r.Name);
   }
  }
  var native=FileVersionInfo.GetVersionInfo(file);foreach(var x in rule.GetProperty("native").EnumerateObject())
  {
   var value=typeof(FileVersionInfo).GetProperty(x.Name)!.GetValue(native);Need(value is bool b?b==x.Value.GetBoolean():value is int n?n==x.Value.GetInt32():(string?)value==x.Value.GetString(),"Original native VERSIONINFO "+x.Name);
  }
  var context=new OwnedContext(Path.GetDirectoryName(file)!);var bridge=context.LoadFromAssemblyPath(Path.Combine(Path.GetDirectoryName(file)!,"Bridge.dll"));Console.WriteLine(bridge.GetType("Bridge")!.GetMethod("Run")!.Invoke(null,new object[]{args[4]=="windows"}));
  Need(context.Assemblies.Single(a=>a.GetName().Name=="System.Text.Encoding.CodePages").Location==file,"Exact source candidate executed");
  if(File.Exists(Path.Combine(Path.GetDirectoryName(file)!,"System.Runtime.CompilerServices.Unsafe.dll")))Need(context.Assemblies.Single(a=>a.GetName().Name=="System.Runtime.CompilerServices.Unsafe").Location==Path.Combine(Path.GetDirectoryName(file)!,"System.Runtime.CompilerServices.Unsafe.dll"),"Exact source Unsafe4.5.2 executed");
  context.Unload();Console.WriteLine("PASS original API/identity/dependencies, all resource strings/binary data and managed/native metadata");
 }
}
