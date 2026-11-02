using System;
using System.Buffers;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Pipelines;
using System.Linq;
using System.Net;
using System.Reflection;
using System.Resources;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Schema;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using System.Xml.Linq;

public sealed class Payload { public string Name {get;set;}=""; public int Value {get;set;} }
[JsonSerializable(typeof(Payload))]
[JsonSourceGenerationOptions(PropertyNamingPolicy=JsonKnownNamingPolicy.CamelCase)]
internal partial class SourceContext:JsonSerializerContext {}
internal static class Program
{
 static void Need(bool value,string message){if(!value)throw new Exception(message);}
 static async Task Main(string[] args)
 {
  var names=new[]{"System.Text.Json","System.Text.Encodings.Web","System.IO.Pipelines"};
  var libraries=new[]{typeof(JsonSerializer).Assembly,typeof(JavaScriptEncoder).Assembly,typeof(Pipe).Assembly};
  foreach(var a in libraries){
   string n=a.GetName().Name!;Need(a.GetName().Version==new Version(10,0,0,0),n+" version");
   Need(Path.GetFullPath(Path.GetDirectoryName(a.Location)!)==Path.GetFullPath(AppContext.BaseDirectory).TrimEnd(Path.DirectorySeparatorChar),n+" source asset location");
   Need(a.GetCustomAttribute<TargetFrameworkAttribute>()?.FrameworkName==".NETCoreApp,Version=v8.0",n+" original framework");
   Need(a.GetCustomAttribute<CLSCompliantAttribute>()?.IsCompliant==true,n+" original CLS policy");
   Need(a.GetCustomAttribute<AssemblyFileVersionAttribute>()?.Version=="10.0.526.11800",n+" source file version");
   Need(a.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion=="10.0.5+081d220c0a773ffb7c6bea6b48727833576a65ef",n+" commit");
   Need(a.GetCustomAttribute<AssemblyDefaultAliasAttribute>()?.DefaultAlias==n,n+" default alias");
   Need(a.GetCustomAttribute<NeutralResourcesLanguageAttribute>()?.CultureName=="en-US",n+" neutral language");
   Need((int)a.GetCustomAttribute<DefaultDllImportSearchPathsAttribute>()!.Paths==2050,n+" DLL search policy");
   var metadata=a.GetCustomAttributes<AssemblyMetadataAttribute>().ToDictionary(x=>x.Key,x=>x.Value);
   foreach(string key in new[]{"Serviceable","PreferInbox","IsTrimmable"})Need(metadata[key]=="True",n+" "+key);
   Console.WriteLine("PASS source identity, target, CLS, versions, aliases, resources and library metadata: "+n);
  }
  using var localization=JsonDocument.Parse(File.ReadAllText(args[1]));int sets=0,strings=0;
  foreach(var item in localization.RootElement.EnumerateArray()){
   var a=libraries.Single(a=>a.GetName().Name==item.GetProperty("assembly").GetString());
   using var stream=a.GetManifestResourceStream(item.GetProperty("resource").GetString()+".resources")!;Need(stream!=null,"Original resource set");
   using var reader=new ResourceReader(stream!);var values=new Dictionary<string,string>();
   foreach(System.Collections.DictionaryEntry v in reader)values.Add((string)v.Key,(string)v.Value!);
   foreach(var v in item.GetProperty("strings").EnumerateObject()){Need(values[v.Name]==v.Value.GetString(),v.Name);strings++;}sets++;
  }
  Console.WriteLine($"PASS all {sets} original resource sets / {strings} strings");
  var refs=Directory.GetFiles(args[2],"*.dll").Where(p=>!names.Contains(Path.GetFileNameWithoutExtension(p))).Concat(libraries.Select(a=>a.Location)).ToArray();
  var api=new Dictionary<string,int>();
  foreach(var n in names){
   var files=new List<string>{Path.Combine(args[0],"src/libraries",n,"ref",n+".cs")};
   if(n=="System.Text.Json"){
    files.Add(Path.Combine(args[0],"src/libraries/System.Text.Json/ref/System.Text.Json.netcoreapp.cs"));
    files.Add(Path.Combine(args[0],"src/libraries/System.Text.Json/ref/System.Text.Json.Typeforwards.netcoreapp.cs"));
    files.Add(Path.Combine(args[0],"src/libraries/System.Private.CoreLib/src/System/Diagnostics/CodeAnalysis/FeatureSwitchDefinitionAttribute.cs"));
   }
   api[n]=ApiGate.CompareSource(n,files,new[]{"NET","NET8_0","NETCOREAPP","NET8_0_OR_GREATER"},libraries.Single(a=>a.GetName().Name==n).Location,refs);
  }
  await Runtime().WaitAsync(TimeSpan.FromSeconds(40));
  Console.WriteLine("PASS generated JSON10 Unicode contracts, schema/DOM/duplicates, pipe serialization/streaming/cancellation/backpressure and encoders");
  File.WriteAllText(args[3],JsonSerializer.Serialize(new{public_api_declarations=api,resource_sets=sets,resource_values=strings,original_metadata_verified=true,runtime_checks_passed=true,source_generated_context_compiled_and_executed=true,full_dependency_goal_complete=false},new JsonSerializerOptions{WriteIndented=true}));
 }
 static async Task Runtime()
 {
  var value=new Payload{Name="π 🚀 <x>",Value=42};var contract=SourceContext.Default.Payload;
  string text=JsonSerializer.Serialize(value,contract);Need(text.Contains("name"),"Generated naming policy");
  var restored=JsonSerializer.Deserialize(text,contract)!;Need(restored.Name==value.Name&&restored.Value==42,"Generated contract round trip");
  JsonNode schema=contract.GetJsonSchemaAsNode();Need(schema.ToJsonString().Contains("name"),"JSON10 schema metadata");
  var node=JsonNode.Parse(text)!;node["value"]=43;Need(node["value"]!.GetValue<int>()==43,"Mutable DOM");
  bool rejected=false;try{using var d=JsonDocument.Parse("{\"v\":1,\"v\":2}",new JsonDocumentOptions{AllowDuplicateProperties=false});}catch(JsonException){rejected=true;}Need(rejected,"New JSON10 duplicate-property rejection");
  using var cancellation=new CancellationTokenSource(TimeSpan.FromSeconds(15));
  var jsonPipe=new Pipe();await JsonSerializer.SerializeAsync(jsonPipe.Writer,value,contract,cancellation.Token);await jsonPipe.Writer.CompleteAsync();
  var pipeValue=await JsonSerializer.DeserializeAsync(jsonPipe.Reader,contract,cancellation.Token);Need(pipeValue!.Name==value.Name,"JSON10 PipeReader/PipeWriter APIs");await jsonPipe.Reader.CompleteAsync();
  var sequencePipe=new Pipe();await sequencePipe.Writer.WriteAsync(Encoding.UTF8.GetBytes("["+text+","+text+"]"),cancellation.Token);await sequencePipe.Writer.CompleteAsync();
  int count=0;await foreach(var p in JsonSerializer.DeserializeAsyncEnumerable(sequencePipe.Reader,contract,cancellation.Token)){Need(p!.Name==value.Name,"Streamed source JSON contract");count++;}Need(count==2,"Streaming count");await sequencePipe.Reader.CompleteAsync();
  var pipe=new Pipe(new PipeOptions(pauseWriterThreshold:4,resumeWriterThreshold:2,useSynchronizationContext:false));
  byte[] bytes=Encoding.UTF8.GetBytes("π 🚀");pipe.Writer.Write(bytes);var flush=pipe.Writer.FlushAsync(cancellation.Token);Need(!flush.IsCompleted,"Real writer backpressure");
  var read=await pipe.Reader.ReadAsync(cancellation.Token);Need(read.Buffer.ToArray().SequenceEqual(bytes),"Source pipe Unicode bytes");pipe.Reader.AdvanceTo(read.Buffer.End);await flush;await pipe.Writer.CompleteAsync();var end=await pipe.Reader.ReadAsync(cancellation.Token);Need(end.IsCompleted,"Pipe completion");pipe.Reader.AdvanceTo(end.Buffer.End);await pipe.Reader.CompleteAsync();
  var cancel=new Pipe();cancel.Reader.CancelPendingRead();var cancelled=await cancel.Reader.ReadAsync(cancellation.Token);Need(cancelled.IsCanceled,"Pending read cancellation");cancel.Reader.AdvanceTo(cancelled.Buffer.End);await cancel.Reader.CompleteAsync();await cancel.Writer.CompleteAsync();
  string html=HtmlEncoder.Default.Encode("<π>\"&");Need(WebUtility.HtmlDecode(html)=="<π>\"&","HTML encoding");
  string escaped=JavaScriptEncoder.Default.Encode("π<");Need(escaped.Contains("\\u"),"Safe JavaScript escaping");Need(JavaScriptEncoder.UnsafeRelaxedJsonEscaping.Encode("π")=="π","Unicode encoder range");Need(Uri.UnescapeDataString(UrlEncoder.Default.Encode("π 🚀"))=="π 🚀","UTF8 URL encoding");
 }
}
