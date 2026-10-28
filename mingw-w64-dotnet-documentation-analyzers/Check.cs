using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CodeActions;
using Microsoft.CodeAnalysis.CodeFixes;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Formatting;
using Microsoft.CodeAnalysis.Diagnostics;
using Microsoft.CodeAnalysis.Host.Mef;
using Microsoft.CodeAnalysis.Text;
class Program
{
 static void Require(bool value,string message){if(!value)throw new Exception(message);}
 static (string text,int markers) Clean(string text)
 {
  int markers=0;var result=new StringBuilder();
  for(int i=0;i<text.Length;)
  {
   if(text.AsSpan(i).StartsWith("[|")){markers++;i+=2;continue;}
   if(text.AsSpan(i).StartsWith("|]")||text.AsSpan(i).StartsWith("|}")){i+=2;continue;}
   if(text.AsSpan(i).StartsWith("$$")){markers++;i+=2;continue;}
   if(text.AsSpan(i).StartsWith("{|")){markers++;int end=text.IndexOf(':',i+2);Require(end>=0,"Markup label");i=end+1;continue;}
   result.Append(text[i++]);
  }
  return(result.ToString().Replace("\r", ""),markers);
 }
 static Type FindType(Assembly assembly,string name)=>assembly.GetTypes().Single(t=>t.FullName==name||t.Name==name);
 static async Task Main(string[] args)
 {
  var analyzerAssembly=Assembly.LoadFrom(Path.Combine(AppContext.BaseDirectory,"DocumentationAnalyzers.dll"));
  var fixAssembly=Assembly.LoadFrom(Path.Combine(AppContext.BaseDirectory,"DocumentationAnalyzers.CodeFixes.dll"));
  foreach(var assembly in new[]{analyzerAssembly,fixAssembly})
  {
   Require(assembly.GetName().Version==new Version(1,0,0,59)&&Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()=="2bc5e20c3ad68793","Published unstable assembly identity");
   Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion=="1.0.0-beta.59+489c06575beee224030ffdc9e91ce43569f32a79","Source identity");
   Require(Path.GetRelativePath(AppContext.BaseDirectory,assembly.Location)==assembly.GetName().Name+".dll","Source implementation location");
  }
  using var inventory=JsonDocument.Parse(File.ReadAllText(args[0]));using var resources=JsonDocument.Parse(File.ReadAllText(args[1]));using var fixtureDoc=JsonDocument.Parse(File.ReadAllText(args[2]));
  var analyzerTypes=analyzerAssembly.GetTypes().Where(t=>t.GetCustomAttributes<DiagnosticAnalyzerAttribute>().Any()).OrderBy(t=>t.FullName).ToArray();
  var fixTypes=fixAssembly.GetTypes().Where(t=>t.GetCustomAttributes<ExportCodeFixProviderAttribute>().Any()).OrderBy(t=>t.FullName).ToArray();
  Require(analyzerTypes.Length==18&&fixTypes.Length==14,"Complete analyzer/fixer inventory");
  Require(analyzerTypes.Select(t=>t.FullName).SequenceEqual(inventory.RootElement.GetProperty("DocumentationAnalyzers").GetProperty("analyzers").EnumerateArray().Select(e=>e.GetString())),"Published analyzer classes");
  Require(fixTypes.Select(t=>t.FullName).SequenceEqual(inventory.RootElement.GetProperty("DocumentationAnalyzers.CodeFixes").GetProperty("code_fixes").EnumerateArray().Select(e=>e.GetString())),"Published code-fix classes");
  var analyzers=analyzerTypes.ToDictionary(t=>t.FullName,t=>(DiagnosticAnalyzer)Activator.CreateInstance(t,true));
  var fixes=fixTypes.ToDictionary(t=>t.FullName,t=>(CodeFixProvider)Activator.CreateInstance(t,true));
  var descriptors=analyzers.Values.SelectMany(a=>a.SupportedDiagnostics).ToArray();Require(descriptors.Length==18&&descriptors.Select(d=>d.Id).Distinct().Count()==18,"All diagnostic descriptors");
  foreach(var entry in inventory.RootElement.GetProperty("DocumentationAnalyzers").GetProperty("diagnostic_ids").EnumerateObject())
  {
   var type=analyzerAssembly.GetType(entry.Name);Require((string)type.GetField("DiagnosticId",BindingFlags.Static|BindingFlags.Public|BindingFlags.NonPublic).GetRawConstantValue()==entry.Value.GetString(),"Published rule ID");
   var descriptor=analyzers[entry.Name].SupportedDiagnostics.Single();Require(descriptor.Id==entry.Value.GetString()&&!string.IsNullOrEmpty(descriptor.Title.ToString())&&!string.IsNullOrEmpty(descriptor.MessageFormat.ToString())&&!string.IsNullOrEmpty(descriptor.Description.ToString()),"Descriptor strings");
  }
  foreach(var provider in fixes.Values)Require(provider.FixableDiagnosticIds.Length>0,"Empty code-fix contract");
  int strings=0,sets=0;
  foreach(var resource in resources.RootElement.EnumerateArray())
  {
   var assembly=resource.GetProperty("assembly").GetString()=="DocumentationAnalyzers"?analyzerAssembly:fixAssembly;string name=resource.GetProperty("resource").GetString()+".resources";
   using var reader=new ResourceReader(assembly.GetManifestResourceStream(name)??throw new Exception(name));var actual=reader.Cast<System.Collections.DictionaryEntry>().ToDictionary(e=>(string)e.Key,e=>(string)e.Value);
   Require(actual.Count==resource.GetProperty("strings").EnumerateObject().Count(),"Resource count");
   foreach(var pair in resource.GetProperty("strings").EnumerateObject()){Require(actual.TryGetValue(pair.Name,out string value)&&value==pair.Value.GetString(),"Source resource "+pair.Name);strings++;}sets++;
  }
  Require(sets==4,"Four complete source resource sets");Console.WriteLine($"PASS published 18 analyzer/14 fixer/18 ID inventories, live descriptors and {sets} resource sets/{strings} strings");
  var references=Directory.GetFiles(args[3],"*.dll").Select(p=>MetadataReference.CreateFromFile(p)).ToArray();
  var host=MefHostServices.Create(new[]{typeof(Workspace).Assembly,typeof(CSharpFormattingOptions).Assembly});
  var passed=new List<string>();var failures=new List<string>();var coveredAnalyzers=new HashSet<string>();var coveredFixes=new HashSet<string>();
  foreach(var fixture in fixtureDoc.RootElement.GetProperty("fixtures").EnumerateArray())
  {
   string label=fixture.GetProperty("label").GetString();
   try
   {
    var analyzerType=FindType(analyzerAssembly,fixture.GetProperty("analyzer").GetString());var analyzer=analyzers[analyzerType.FullName];
    var options=new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary).WithSpecificDiagnosticOptions(analyzer.SupportedDiagnostics.ToDictionary(d=>d.Id,_=>ReportDiagnostic.Warn));
    using var workspace=new AdhocWorkspace(host);var project=workspace.AddProject(ProjectInfo.Create(ProjectId.CreateNewId(),VersionStamp.Create(),"OwnedDoc","OwnedDoc",LanguageNames.CSharp,compilationOptions:options,parseOptions:new CSharpParseOptions(LanguageVersion.CSharp12,DocumentationMode.Diagnose),metadataReferences:references));
    var input=Clean(fixture.GetProperty("source").GetString());var document=workspace.AddDocument(project.Id,"owned.cs",SourceText.From(input.text,Encoding.UTF8));var compilation=await document.Project.GetCompilationAsync();
    var diagnostics=await compilation.WithAnalyzers(ImmutableArray.Create(analyzer)).GetAnalyzerDiagnosticsAsync();Require(!diagnostics.Any(d=>d.Id=="AD0001"),"Analyzer exception: "+string.Join(";",diagnostics));
    bool configured=fixture.TryGetProperty("configured",out var configuredValue)&&configuredValue.GetBoolean();bool isFix=fixture.GetProperty("expected").ValueKind!=JsonValueKind.Null;
    if(!isFix&&!configured)Require(diagnostics.Length==input.markers,$"Diagnostic count expected={input.markers} actual={diagnostics.Length}");
    coveredAnalyzers.Add(analyzerType.FullName);
    if(isFix)
    {
     string expected=Clean(fixture.GetProperty("expected").GetString()).text;var fixType=FindType(fixAssembly,fixture.GetProperty("fix").GetString());var provider=fixes[fixType.FullName];
     bool compilerWarnings=fixture.TryGetProperty("compilerWarnings",out var warningValue)&&warningValue.GetBoolean();
     for(int iteration=0;iteration<50;iteration++)
     {
      document=workspace.CurrentSolution.GetDocument(document.Id);compilation=await document.Project.GetCompilationAsync();
      var reported=(await compilation.WithAnalyzers(ImmutableArray.Create(analyzer)).GetAnalyzerDiagnosticsAsync()).Where(d=>provider.FixableDiagnosticIds.Contains(d.Id)).ToList();
      if(compilerWarnings)reported.AddRange(compilation.GetDiagnostics().Where(d=>provider.FixableDiagnosticIds.Contains(d.Id)));
      bool changed=false;
      foreach(var diagnostic in reported.OrderBy(d=>d.Location.SourceSpan.Start))
      {
       var actions=new List<CodeAction>();await provider.RegisterCodeFixesAsync(new CodeFixContext(document,diagnostic,(a,_)=>actions.Add(a),CancellationToken.None));if(actions.Count==0)continue;
       var action=actions[0];while(!action.NestedActions.IsEmpty)action=action.NestedActions[0];
       string before=(await document.GetTextAsync()).ToString();foreach(var operation in await action.GetOperationsAsync(CancellationToken.None))operation.Apply(workspace,CancellationToken.None);
       string after=(await workspace.CurrentSolution.GetDocument(document.Id).GetTextAsync()).ToString();coveredFixes.Add(fixType.FullName);
       if(before!=after){changed=true;break;}
      }
      if(!changed)break;
     }
     string actual=(await workspace.CurrentSolution.GetDocument(document.Id).GetTextAsync()).ToString().Replace("\r", "");
     Require(actual==expected,"Fixed text mismatch\nEXPECTED:\n"+expected+"\nACTUAL:\n"+actual);
    }
    passed.Add(label);
   }
   catch(Exception error){failures.Add(label+": "+error);Console.WriteLine("FAIL "+label+": "+error.Message);}
  }
  Console.WriteLine($"Upstream vectors passed={passed.Count} failed={failures.Count}; analyzer coverage={coveredAnalyzers.Count}/18 code-fix action coverage={coveredFixes.Count}/14");
  File.WriteAllText(args[4],JsonSerializer.Serialize(new{passed,failures,analyzers=coveredAnalyzers.OrderBy(x=>x),code_fixes=coveredFixes.OrderBy(x=>x)},new JsonSerializerOptions{WriteIndented=true}));
  Require(failures.Count==0,"Upstream fixture failures");Require(coveredAnalyzers.Count==18&&coveredFixes.Count==14,"Complete analyzer and actual code-fix action coverage");
  foreach(System.Diagnostics.ProcessModule module in System.Diagnostics.Process.GetCurrentProcess().Modules)Require(!module.FileName.Replace('\\','/').Contains("/Microsoft.NET/Framework",StringComparison.OrdinalIgnoreCase),"Framework implementation loaded");
  Console.WriteLine("PASS all extracted upstream diagnostic/code-fix vectors, including CommonMark-backed Markdown conversion, and no Framework implementations");
 }
}
