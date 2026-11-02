using System;
using System.Collections;
using System.CommandLine;
using System.CommandLine.Parsing;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Resources;
using System.Runtime.Versioning;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.Xml;
using System.Xml.Linq;
internal static class Check {
 static void Require(bool value,string message){if(!value)throw new Exception(message);}
 sealed class Output:Xunit.Abstractions.ITestOutputHelper {public void WriteLine(string text){}}
 static async Task Main(string[] args){
  string source=args[0],tfm=args[1],expectedFile=args[2];var assembly=typeof(RootCommand).Assembly;var identity=assembly.GetName();
  Require(identity.Version!.ToString()=="2.0.2.0"&&Convert.ToHexString(identity.GetPublicKeyToken()!).ToLowerInvariant()=="31bf3856ad364e35","original assembly identity");
  Require(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>()!.Version=="2.0.225.61305","original file version");
  Require(assembly.GetCustomAttribute<TargetFrameworkAttribute>()!.FrameworkName==(tfm=="net10.0"?".NETCoreApp,Version=v10.0":".NETStandard,Version=v2.0"),"original framework");
  Require(assembly.GetCustomAttribute<CLSCompliantAttribute>()!.IsCompliant,"original CLS attribute");
  using(var peFile=File.OpenRead(assembly.Location))using(var pe=new PEReader(peFile))using(var pdbFile=File.OpenRead(Path.ChangeExtension(assembly.Location,".pdb")))using(var provider=MetadataReaderProvider.FromPortablePdbStream(pdbFile)){
   var cv=pe.ReadDebugDirectory().Single(e=>e.Type==DebugDirectoryEntryType.CodeView);var id=provider.GetMetadataReader().DebugMetadataHeader!.Id.ToArray();Require(pe.ReadCodeViewDebugDirectoryData(cv).Guid==new Guid(id.Take(16).ToArray())&&cv.Stamp==BitConverter.ToUInt32(id,16),"portable PDB association");
  }
  int strings=0;using(var xml=new XmlTextReader(Path.Combine(source,"src/System.CommandLine/Properties/Resources.resx"))){xml.WhitespaceHandling=WhitespaceHandling.All;using var set=new ResourceSet(assembly.GetManifestResourceStream("System.CommandLine.Properties.Resources.resources")!);foreach(var data in XDocument.Load(xml,LoadOptions.PreserveWhitespace).Root!.Elements("data")){Require(set.GetString(data.Attribute("name")!.Value)==data.Element("value")!.Value,"neutral resource");strings++;}}
  var manager=new ResourceManager("System.CommandLine.Properties.Resources",assembly);using var translations=JsonDocument.Parse(File.ReadAllText(expectedFile));
  foreach(var item in translations.RootElement.EnumerateArray()){
   var culture=CultureInfo.GetCultureInfo(item.GetProperty("culture").GetString()!);var satellite=assembly.GetSatelliteAssembly(culture);Require(satellite.GetName().Version==identity.Version&&satellite.GetName().CultureName==culture.Name&&Convert.ToHexString(satellite.GetName().GetPublicKeyToken()!)==Convert.ToHexString(identity.GetPublicKeyToken()!),"satellite identity");using var set=new ResourceSet(satellite.GetManifestResourceStream("System.CommandLine.Properties.Resources."+culture.Name+".resources")!);foreach(var v in item.GetProperty("strings").EnumerateObject()){Require(set.GetString(v.Name)==v.Value.GetString()&&manager.GetString(v.Name,culture)==v.Value.GetString(),"translated resource "+culture+"/"+v.Name);strings++;}
  }
  var tests=new System.CommandLine.Tests.SplitCommandLineTests(new Output());int cases=0;
  foreach(var method in tests.GetType().GetMethods()){
   if(method.GetCustomAttribute<Xunit.FactAttribute>()!=null){method.Invoke(tests,null);cases++;}
   foreach(var row in method.GetCustomAttributes<Xunit.InlineDataAttribute>()){method.Invoke(tests,row.Data);cases++;}
  }
  Require(cases==9,"all selected upstream tokenization cases");
  var name=new Option<string>("--name","-n"){Required=true};var count=new Option<int>("--count","-c"){DefaultValueFactory=_=>1};var command=new RootCommand("Owned Unicode parser"){name,count};int runs=0;command.SetAction(result=>{Require(result.GetValue(name)=="Grüsse 世界"&&result.GetValue(count)==3,"typed invocation values");runs++;return 23;});
  var parse=command.Parse(new[]{"-n","Grüsse 世界","--count=3"});Require(parse.Errors.Count==0&&parse.Invoke()==23&&runs==1,"sync action and exit status");
  var response=Path.GetFullPath("owned args 世界.rsp");File.WriteAllText(response,"--name \"Grüsse 世界\" --count 3");Require(command.Parse(new[]{"@"+response}).Invoke()==23&&runs==2,"Unicode response file");
  Require(command.Parse(Array.Empty<string>()).Errors.Count>0,"required option");Require(command.Parse(new[]{"--name","X","--count","bad"}).Errors.Count>0,"typed conversion error");Require(command.Parse(new[]{"--name","X","--unexpected"}).Errors.Count>0,"unknown option");
  var color=new Option<string>("--color");color.AcceptOnlyFromAmong("amber","azure","blue");var completion=new RootCommand{color};Require(completion.Parse("--color a").GetCompletions().Select(c=>c.Label).OrderBy(s=>s).SequenceEqual(new[]{"amber","azure"}),"value completion");
  using var output=new StringWriter();using var error=new StringWriter();var config=new InvocationConfiguration{Output=output,Error=error};Require(command.Parse("--help").Invoke(config)==0&&output.ToString().Contains("--name"),"help action/output");
  var asyncCommand=new RootCommand();using var cancellation=new CancellationTokenSource();asyncCommand.SetAction(async (_,token)=>{await Task.Yield();Require(token.CanBeCanceled,"linked cancellation token");cancellation.Cancel();Require(token.IsCancellationRequested,"cancellation propagation");return 29;});Require(await asyncCommand.Parse(Array.Empty<string>()).InvokeAsync(cancellationToken:cancellation.Token)==29,"async action and exit status");
  if(tfm=="netstandard2.0"){
   var memory=Assembly.Load("System.Memory");Require(!memory.GetCustomAttributesData().Any(a=>a.AttributeType.FullName=="System.Runtime.CompilerServices.ReferenceAssemblyAttribute"),"runtime must reject reference-only substitution");Require(Path.GetFullPath(memory.Location).StartsWith(Path.GetFullPath(Environment.GetEnvironmentVariable("DOTNET_ROOT")!),StringComparison.OrdinalIgnoreCase),"source framework Memory implementation/facade");
  }
  Console.WriteLine($"PASS {tfm} on {Environment.Version}: original identity/PDB/CLS, {strings} exact resources, 14 satellite identities, {cases} unchanged upstream tokenization cases, typed parsing/errors, response files, completions, help, sync/async actions and exit status");
 }
}
