using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CodeActions;
using Microsoft.CodeAnalysis.CodeFixes;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Formatting;
using Microsoft.CodeAnalysis.Diagnostics;
using Microsoft.CodeAnalysis.Formatting;
using Microsoft.CodeAnalysis.Host.Mef;
using Microsoft.CodeAnalysis.Text;

class CheckFixtures
{
 sealed class Options:AnalyzerConfigOptions
 {
  readonly string tabs,tabSize,indentationSize;
  public Options(bool tabs,int tabSize,int indentationSize){this.tabs=tabs?"tab":"space";this.tabSize=tabSize.ToString();this.indentationSize=indentationSize.ToString();}
  public override bool TryGetValue(string key,out string value)
  {value=key switch{"indent_size"=>indentationSize,"indent_style"=>tabs,"tab_width"=>tabSize,_=>null};return value!=null;}
 }
 sealed class Config:AnalyzerConfigOptionsProvider
 {
  readonly Options options;
  public Config(bool tabs,int tabSize,int indentationSize){options=new Options(tabs,tabSize,indentationSize);}
  public override AnalyzerConfigOptions GlobalOptions=>options;
  public override AnalyzerConfigOptions GetOptions(SyntaxTree tree)=>options;
  public override AnalyzerConfigOptions GetOptions(AdditionalText textFile)=>options;
 }
 sealed class XmlResolver:XmlReferenceResolver
 {
  readonly Dictionary<string,string> files;
  public XmlResolver(JsonElement entries){files=entries.EnumerateObject().ToDictionary(e=>e.Name,e=>e.Value.GetString());}
  public override string ResolveReference(string path,string baseFilePath)=>files.ContainsKey(Path.GetFileName(path))?Path.GetFileName(path):null;
  public override Stream OpenRead(string resolvedPath)=>new MemoryStream(Encoding.UTF8.GetBytes(files[resolvedPath]));
  public override bool Equals(object other)=>ReferenceEquals(this,other);
  public override int GetHashCode()=>System.Runtime.CompilerServices.RuntimeHelpers.GetHashCode(this);
 }
 sealed class TextFile:AdditionalText
 {
  readonly string text;public TextFile(string text){this.text=text;}
  public override string Path=>"stylecop.json";
  public override SourceText GetText(CancellationToken token=default)=>SourceText.From(text,Encoding.UTF8);
 }
 static void Require(bool value,string message){if(!value)throw new Exception(message);}
 static (string text,int markers) Clean(string text)
 {
  int markers=0;var result=new StringBuilder();
  for(int i=0;i<text.Length;)
  {
   if(text.AsSpan(i).StartsWith("[|")){markers++;i+=2;continue;}
   if(text.AsSpan(i).StartsWith("|]")||text.AsSpan(i).StartsWith("|}")){i+=2;continue;}
   if(text.AsSpan(i).StartsWith("$$")){i+=2;continue;}
   if(text.AsSpan(i).StartsWith("{|"))
   {
    int end=text.IndexOf(':',i+2);
    if(end>=0&&!text.Substring(i+2,end-i-2).Any(c=>char.IsWhiteSpace(c)||c is '|' or '{' or '}')){markers++;i=end+1;continue;}
   }
   result.Append(text[i++]);
  }
  return(result.ToString(),markers);
 }
 static async Task Main(string[] args)
 {
  using var fixtureDocument=JsonDocument.Parse(File.ReadAllText(args[0]));
  var assembly=Assembly.LoadFrom(Path.Combine(AppContext.BaseDirectory,"StyleCop.Analyzers.dll"));
  var fixAssembly=Assembly.LoadFrom(Path.Combine(AppContext.BaseDirectory,"StyleCop.Analyzers.CodeFixes.dll"));
  var references=Directory.GetFiles(args[1],"*.dll").Concat(new[]{typeof(Compilation).Assembly.Location,typeof(CSharpCompilation).Assembly.Location}).Select(p=>MetadataReference.CreateFromFile(p)).ToArray();
  var host=MefHostServices.Create(new[]{typeof(Workspace).Assembly,typeof(CSharpFormattingOptions).Assembly});
  var passed=new List<string>();var failures=new List<object>();var analyzerCoverage=new HashSet<string>();var positiveCoverage=new HashSet<string>();var fixes=new HashSet<string>();
  int index=0;
  foreach(var fixture in fixtureDocument.RootElement.GetProperty("fixtures").EnumerateArray())
  {
   string label=fixture.GetProperty("label").GetString();
   try
   {
    var analyzerType=assembly.GetTypes().Single(t=>t.FullName==fixture.GetProperty("analyzer").GetString()||t.Name==fixture.GetProperty("analyzer").GetString());
    var analyzer=(DiagnosticAnalyzer)Activator.CreateInstance(analyzerType,true);
    var options=new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary,allowUnsafe:true).WithSpecificDiagnosticOptions(analyzer.SupportedDiagnostics.Select(d=>d.Id).Distinct().ToDictionary(d=>d,_=>ReportDiagnostic.Warn)).WithXmlReferenceResolver(new XmlResolver(fixture.GetProperty("xmlReferences")));
    var language=Enum.Parse<LanguageVersion>(fixture.GetProperty("language").GetString());
    using var workspace=new AdhocWorkspace(host);
    bool useTabs=fixture.GetProperty("useTabs").GetBoolean();int tabSize=fixture.GetProperty("tabSize").GetInt32(),indentationSize=fixture.GetProperty("indentationSize").GetInt32();
    workspace.Options=workspace.Options.WithChangedOption(FormattingOptions.NewLine,LanguageNames.CSharp,"\n").WithChangedOption(FormattingOptions.IndentationSize,LanguageNames.CSharp,indentationSize).WithChangedOption(FormattingOptions.TabSize,LanguageNames.CSharp,tabSize).WithChangedOption(FormattingOptions.UseTabs,LanguageNames.CSharp,useTabs);
    var project=workspace.AddProject(ProjectInfo.Create(ProjectId.CreateNewId(),VersionStamp.Create(),"UpstreamStyleCop","UpstreamStyleCop",LanguageNames.CSharp,compilationOptions:options,parseOptions:new CSharpParseOptions(language,DocumentationMode.Diagnose),metadataReferences:references));
    string settings=fixture.GetProperty("settings").GetString();
    if(useTabs||tabSize!=4||indentationSize!=4)
    {
     var json=settings==null?new JsonObject():JsonNode.Parse(settings,new JsonNodeOptions(),new JsonDocumentOptions{AllowTrailingCommas=true,CommentHandling=JsonCommentHandling.Skip});
     json["settings"]??=new JsonObject();json["settings"]["indentation"]=new JsonObject{["useTabs"]=useTabs,["tabSize"]=tabSize,["indentationSize"]=indentationSize};settings=json.ToJsonString();
    }
    if(settings!=null)
    {
     var changed=project.AddAdditionalDocument("stylecop.json",SourceText.From(settings,Encoding.UTF8)).Project;
     Require(workspace.TryApplyChanges(changed.Solution),"Additional settings document");project=workspace.CurrentSolution.GetProject(project.Id);
    }
    var analyzerOptions=new AnalyzerOptions(settings==null?ImmutableArray<AdditionalText>.Empty:ImmutableArray.Create<AdditionalText>(new TextFile(settings)),new Config(useTabs,tabSize,indentationSize));
    var input=Clean(fixture.GetProperty("source").GetString());var document=workspace.AddDocument(project.Id,"Test0.cs",SourceText.From(input.text,Encoding.UTF8));
    var compilation=await document.Project.GetCompilationAsync();
    async Task<ImmutableArray<Diagnostic>> Analyze(Compilation c)
    {
     var diagnostic=await c.WithAnalyzers(ImmutableArray.Create(analyzer),analyzerOptions).GetAnalyzerDiagnosticsAsync();
     Require(!diagnostic.Any(d=>d.Id=="AD0001"),"Analyzer exception "+string.Join(";",diagnostic.Where(d=>d.Id=="AD0001")));
     return diagnostic.OrderBy(d=>d.Location.SourceSpan.Start).ToImmutableArray();
    }
    var diagnostics=await Analyze(compilation);int originalCount=fixture.GetProperty("diagnostics").GetInt32();
    int expectedCount=originalCount-fixture.GetProperty("compilerDiagnostics").GetInt32();
    int markedCompilerCount=System.Text.RegularExpressions.Regex.Matches(fixture.GetProperty("source").GetString(),@"\{\|CS\d+:").Count;
    if(originalCount==0&&input.markers>0)expectedCount=input.markers-markedCompilerCount;
    Require(diagnostics.Length==expectedCount,$"Diagnostic count expected={expectedCount} actual={diagnostics.Length}: "+string.Join(";",diagnostics.Select(d=>d.ToString())));
    analyzerCoverage.Add(analyzerType.FullName);if(diagnostics.Length>0)positiveCoverage.Add(analyzerType.FullName);
    bool isFix=fixture.GetProperty("expected").ValueKind!=JsonValueKind.Null;
    string completedFix=null;
    if(isFix)
    {
     string providerName=fixture.GetProperty("fix").GetString();
     var providerType=fixAssembly.GetTypes().Single(t=>t.FullName==providerName||t.Name==providerName);
     var provider=(CodeFixProvider)Activator.CreateInstance(providerType,true);
     string expected=Clean(fixture.GetProperty("expected").GetString()).text.Replace("\r","");
     for(int iteration=0;iteration<100;iteration++)
     {
      document=workspace.CurrentSolution.GetDocument(document.Id);compilation=await document.Project.GetCompilationAsync();
      diagnostics=await Analyze(compilation);bool changed=false;
      foreach(var diagnostic in diagnostics.Where(d=>provider.FixableDiagnosticIds.Contains(d.Id)))
      {
       var actions=new List<CodeAction>();await provider.RegisterCodeFixesAsync(new CodeFixContext(document,diagnostic,(a,_)=>actions.Add(a),CancellationToken.None));
       if(actions.Count==0)continue;
       int actionIndex=fixture.GetProperty("actionIndex").GetInt32();Require(actionIndex<actions.Count,"Code action index");var action=actions[actionIndex];while(!action.NestedActions.IsEmpty)action=action.NestedActions[0];
       string before=(await document.GetTextAsync()).ToString();
       foreach(var operation in await action.GetOperationsAsync(CancellationToken.None))operation.Apply(workspace,CancellationToken.None);
       string after=(await workspace.CurrentSolution.GetDocument(document.Id).GetTextAsync()).ToString();
       if(before!=after){completedFix=providerType.FullName;changed=true;break;}
      }
      if(!changed)break;
     }
     string actual=(await workspace.CurrentSolution.GetDocument(document.Id).GetTextAsync()).ToString().Replace("\r","");
     Require(actual==expected,"Fixed text mismatch\nEXPECTED:\n"+expected+"\nACTUAL:\n"+actual);
    }
    if(completedFix!=null)fixes.Add(completedFix);
    passed.Add(label);
   }
   catch(Exception error){failures.Add(new{label,error=error.ToString()});Console.WriteLine("FAIL "+label+": "+error.Message);}
   if(++index%100==0)Console.WriteLine($"PROGRESS checked={index} passed={passed.Count} failed={failures.Count} analyzers={analyzerCoverage.Count} positive={positiveCoverage.Count} fixes={fixes.Count}");
   if(index%100==0)File.WriteAllText(args[2],JsonSerializer.Serialize(new{passed,failures,analyzers=analyzerCoverage.OrderBy(x=>x),positive_analyzers=positiveCoverage.OrderBy(x=>x),code_fixes=fixes.OrderBy(x=>x)},new JsonSerializerOptions{WriteIndented=true}));
  }
  var special=await CheckSpecialFixes.Run(args[1]);
  foreach(var item in special.failures)failures.Add(new{label=item.Key,error=item.Value});
  foreach(var provider in special.providers)fixes.Add(provider);
  File.WriteAllText(args[2],JsonSerializer.Serialize(new{passed,owned_passed=special.passed,failures,analyzers=analyzerCoverage.OrderBy(x=>x),positive_analyzers=positiveCoverage.OrderBy(x=>x),code_fixes=fixes.OrderBy(x=>x)},new JsonSerializerOptions{WriteIndented=true}));
  Console.WriteLine($"RESULT checked={index} passed={passed.Count} failed={failures.Count} analyzers={analyzerCoverage.Count} positive={positiveCoverage.Count} fixes={fixes.Count}");
  Require(failures.Count==0,"Upstream fixture failures");
 }
}
