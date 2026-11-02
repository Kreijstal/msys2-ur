using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;
static class Program
{
 static void Need(bool value,string label){if(!value)throw new Exception(label);}
 static string Args(CustomAttribute a)=>string.Join("|",a.ConstructorArguments.Select(x=>Convert.ToString(x.Value,System.Globalization.CultureInfo.InvariantCulture)));
 static void Main(string[] args)
 {
  bool inspect=args[0]=="--check";int offset=inspect?1:0;
  using var policy=JsonDocument.Parse(File.ReadAllText(args[offset]));var p=policy.RootElement;
  using var baseline=JsonDocument.Parse(File.ReadAllText(args[offset+1]));var original=baseline.RootElement.GetProperty("netstandard.dll");
  if(inspect){Verify(args[3],p,original);return;}
  var identity=AssemblyNameReference.Parse(p.GetProperty("identity").GetString()!);
  var name=new AssemblyNameDefinition("source-facade-metadata-bootstrap",identity.Version){PublicKey=Convert.FromHexString(string.Concat(File.ReadAllText(args[2]).Where(c=>!char.IsWhiteSpace(c))))};
  Need(name.PublicKeyToken.SequenceEqual(identity.PublicKeyToken),"Original Open public-key identity");
  using var assembly=AssemblyDefinition.CreateAssembly(name,"netstandard.dll",ModuleKind.Dll);var module=assembly.MainModule;
  name.Attributes=(AssemblyAttributes)p.GetProperty("assemblyAttributes").GetInt32();module.Attributes=(ModuleAttributes)p.GetProperty("moduleAttributes").GetInt32();module.RuntimeVersion=p.GetProperty("runtimeVersion").GetString();
  module.AssemblyReferences.Clear();foreach(var r in p.GetProperty("references").EnumerateArray())module.AssemblyReferences.Add(AssemblyNameReference.Parse(r.GetString()!));
  var runtime=module.AssemblyReferences.Single(r=>r.Name=="System.Runtime");
  var exports=new Dictionary<string,ExportedType>(StringComparer.Ordinal);
  foreach(var t in p.GetProperty("exportedTypes").EnumerateArray())
  {
   var scope=module.AssemblyReferences.Single(r=>r.FullName==t.GetProperty("scope").GetString());
   var type=new ExportedType(t.GetProperty("namespace").GetString(),t.GetProperty("name").GetString(),module,scope){Attributes=(TypeAttributes)t.GetProperty("attributes").GetInt32()};
   exports.Add(t.GetProperty("fullName").GetString()!,type);module.ExportedTypes.Add(type);
  }
  foreach(var t in p.GetProperty("exportedTypes").EnumerateArray())if(t.GetProperty("declaringType").ValueKind!=JsonValueKind.Null)exports[t.GetProperty("fullName").GetString()!].DeclaringType=exports[t.GetProperty("declaringType").GetString()!];
  var voidType=module.TypeSystem.Void;voidType.Scope=runtime;var stringType=module.TypeSystem.String;stringType.Scope=runtime;
  foreach(var attribute in original.GetProperty("attributes").EnumerateArray())
  {
   string full=attribute.GetProperty("type").GetString()!;Need(full.StartsWith("System.Reflection.",StringComparison.Ordinal),"Only original string assembly attributes");int dot=full.LastIndexOf('.');
   var type=new TypeReference(full.Substring(0,dot),full.Substring(dot+1),module,runtime);var ctor=new MethodReference(".ctor",voidType,type){HasThis=true};
   foreach(var value in attribute.GetProperty("arguments").EnumerateArray())ctor.Parameters.Add(new ParameterDefinition(stringType));
   var added=new CustomAttribute(ctor);foreach(var value in attribute.GetProperty("arguments").EnumerateArray())added.ConstructorArguments.Add(new CustomAttributeArgument(stringType,value.GetString()));assembly.CustomAttributes.Add(added);
  }
  foreach(var r in module.AssemblyReferences.Where(r=>!p.GetProperty("references").EnumerateArray().Any(x=>x.GetString()==r.FullName)).ToArray())module.AssemblyReferences.Remove(r);
  name.Name=identity.Name;
  assembly.Write(args[3]);
  Verify(args[3],p,original);
 }
 static void Verify(string file,JsonElement p,JsonElement original)
 {
  using var read=AssemblyDefinition.ReadAssembly(file);Need(read.Name.FullName==p.GetProperty("identity").GetString(),"Facade identity");
  Need(read.MainModule.Types.Count==p.GetProperty("definedTypeCount").GetInt32() && !read.MainModule.Types.SelectMany(t=>t.Methods).Any(m=>m.HasBody),"Original facade contains no implementation methods");
  Need(read.MainModule.AssemblyReferences.Select(r=>r.FullName).SequenceEqual(p.GetProperty("references").EnumerateArray().Select(x=>x.GetString())),"All original minimum-version reference scopes");
  Need(read.MainModule.ExportedTypes.Count==p.GetProperty("exportedTypes").GetArrayLength(),"All original exported types");
  foreach(var expected in p.GetProperty("exportedTypes").EnumerateArray())
  {
   var actual=read.MainModule.ExportedTypes.Single(t=>t.FullName==expected.GetProperty("fullName").GetString());
   Need(actual.Name==expected.GetProperty("name").GetString() && actual.Namespace==expected.GetProperty("namespace").GetString() && (int)actual.Attributes==expected.GetProperty("attributes").GetInt32() && actual.Scope.ToString()==expected.GetProperty("scope").GetString() && actual.DeclaringType?.FullName==expected.GetProperty("declaringType").GetString(),"Exact exported type "+actual.FullName);
  }
  Need(!read.CustomAttributes.Any(a=>a.AttributeType.FullName=="System.Runtime.CompilerServices.ReferenceAssemblyAttribute"),"Original facade has no reference marker");
  Need(read.CustomAttributes.Count==original.GetProperty("attributes").GetArrayLength(),"Original assembly attribute count");
  foreach(var attribute in original.GetProperty("attributes").EnumerateArray())Need(read.CustomAttributes.Any(a=>a.AttributeType.FullName==attribute.GetProperty("type").GetString() && Args(a)==string.Join("|",attribute.GetProperty("arguments").EnumerateArray().Select(x=>x.GetString()))),"Original facade assembly attribute");
  Console.WriteLine("PASS source metadata facade: "+read.MainModule.ExportedTypes.Count+" exact original forwarders, "+read.MainModule.AssemblyReferences.Count+" scopes, original identity/attributes, zero implementation methods");
 }
}
