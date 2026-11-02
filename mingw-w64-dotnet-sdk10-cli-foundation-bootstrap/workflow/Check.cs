using System;
using System.CommandLine;
using System.CommandLine.StaticCompletions;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.DotNet.Cli.CommandLine;
using Microsoft.DotNet.Cli.Utils;
using Microsoft.DotNet.Configurer;
using Microsoft.DotNet.NativeWrapper;
using Microsoft.Extensions.EnvironmentAbstractions;
using Microsoft.NET.Sdk.WorkloadManifestReader;
using Microsoft.Win32.Msi;
internal static class Check {
 static void Require(bool value,string message){if(!value)throw new Exception(message);}
 static async Task Main(string[] args){
  string prefix=args[0],source=args[1];string root8=Path.Combine(prefix,"lib/dotnet"),root10=Path.Combine(prefix,"lib/dotnet10");
  string work=Path.GetFullPath("owned Grüsse 世界");Directory.CreateDirectory(work);var file=new FilePath(Path.Combine(work,"file λ.txt"));Require(file.GetDirectoryPath().Value==work,"original FilePath/DirectoryPath abstractions");
  var sentinel=new FileSentinel(file);Require(!sentinel.Exists(),"fresh source sentinel");sentinel.Create();Require(sentinel.Exists()&&File.ReadAllBytes(file.Value).Length==0,"original sentinel creates owned empty file");sentinel.Create();
  int writes=0;var cache=new UserLevelCacheWriter();var cacheFile=Path.Combine(work,"cache 世界.txt");Require(cache.RunWithCacheInFilePath(cacheFile,()=>{writes++;return "Grüsse 世界";})=="Grüsse 世界","owned cache write");Require(cache.RunWithCacheInFilePath(cacheFile,()=>{writes++;return "wrong";})=="Grüsse 世界"&&writes==1,"owned cache read");
  Require(Path.GetFullPath(CliFolderPathCalculator.DotnetHomePath)==Path.GetFullPath(Environment.GetEnvironmentVariable("DOTNET_CLI_HOME")!),"process-local CLI home");
  Require(PathUtility.GetPathWithForwardSlashes(PathUtility.GetRelativePath(new DirectoryInfo(work),new FileInfo(file.Value)))=="file λ.txt","original Unicode path utility");int attempts=0;int retried=await FileAccessRetrier.RetryOnFileAccessFailure(()=>{if(++attempts<3)throw new IOException("owned synthetic transient");return 41;},"owned exhausted",maxRetries:3,sleepDuration:TimeSpan.FromMilliseconds(1));Require(retried==41&&attempts==3,"original bounded file retry");
  var amount=new Option<int>("--amount").AsSpanParsable().ForwardAsSingle(v=>"/p:Amount="+v.ToString(CultureInfo.InvariantCulture));var verbose=new Option<bool>("--verbose").ForwardIfEnabled("/v:diag");var command=new RootCommand("Owned CLI tree"){amount,verbose};
  var parsed=command.Parse("--amount 37 --verbose");Require(parsed.Errors.Count==0&&parsed.GetValue(amount)==37,"original span parser");Require(parsed.OptionValuesToBeForwarded().SequenceEqual(new[]{"/p:Amount=37","/v:diag"}),"original MSBuild option forwarding");Require(command.Parse("--amount bad").Errors.Count>0,"span parser conversion error");Require(command.Parse(Array.Empty<string>()).OptionValuesToBeForwarded().Count()==0,"absent flags not forwarded");
  var completionCommand=new System.CommandLine.Command("owned-cli");var color=new Option<string>("--color");color.AcceptOnlyFromAmong("amber","azure");completionCommand.Options.Add(color);Require(CompletionsCommand.DefaultShells.Length==5,"five original shell providers");
  foreach(var shell in CompletionsCommand.DefaultShells){string script=shell.GenerateCompletions(completionCommand);Require(script.Length>100&&((shell.ArgumentName=="fish"||shell.ArgumentName=="nushell")?script.Contains("dotnet complete"):script.Contains("owned-cli")),"original completion script "+shell.ArgumentName);File.WriteAllText(Path.Combine(work,"completion."+shell.Extension),script);}
  string upstream=Path.Combine(source,"test/TestAssets/TestWorkloads/manifests/Microsoft.NET.Sdk.TestWorkload/WorkloadManifest.json");using(var stream=File.OpenRead(upstream)){var manifest=WorkloadManifestReader.ReadWorkloadManifest("owned-test",stream,upstream);Require(manifest.Version=="6.0.0-preview1"&&manifest.Workloads.Count==2&&manifest.Packs.Count==2,"unchanged upstream workload manifest");var alias=manifest.Packs.Values.Single(p=>p.IsAlias).TryGetAliasForRuntimeIdentifiers(new[]{"win"});Require(alias!=null&&alias.ToString()=="Microsoft.NET.Sdk.TestWorkload.Pack.Win","original RID pack alias");}
  byte[] unicode=Encoding.UTF8.GetBytes("{\"version\":\"10.0.0\",\"workloads\":{\"owned\":{\"description\":\"Grüsse 世界\",\"packs\":[\"Owned.Pack\"]}},\"packs\":{\"Owned.Pack\":{\"kind\":\"sdk\",\"version\":\"1.0.0\"}}}");using(var stream=new MemoryStream(unicode)){var manifest=WorkloadManifestReader.ReadWorkloadManifest("owned",stream,Path.Combine(work,"manifest.json"));Require(manifest.Workloads.Count==1&&manifest.Packs.Count==1,"owned Unicode workload manifest");}
  using(var legacy=new MemoryStream(Encoding.UTF8.GetBytes("{\"version\":42}"))){Require(WorkloadManifestReader.ReadWorkloadManifest("legacy",legacy,"owned-legacy.json").Version=="42.0.0","original legacy integer manifest version");}
  bool malformed=false;try{using var stream=new MemoryStream(Encoding.UTF8.GetBytes("{\"version\":true}"));WorkloadManifestReader.ReadWorkloadManifest("bad",stream,"owned-invalid.json");}catch(Exception ex) when(ex.GetType().Name=="WorkloadManifestFormatException"){malformed=true;}Require(malformed,"invalid workload manifest rejected");
  var bundle=new NETBundlesNativeWrapper();var environment=bundle.GetDotnetEnvironmentInfo(root10);GC.Collect(2,GCCollectionMode.Forced,true,true);Require(environment.RuntimeInfo.Any(r=>r.Name=="Microsoft.NETCore.App"&&r.Version.ToString()=="10.0.5"),"native source NET10 runtime enumeration and retained callback data");Require(NETCoreSdkResolverNativeWrapper.GetAvailableSdks(root8)!.Any(p=>Path.GetFileName(p)=="8.0.131"),"native source SDK enumeration");
  string jsonDir=Path.Combine(work,"global-json 世界");Directory.CreateDirectory(jsonDir);File.WriteAllText(Path.Combine(jsonDir,"global.json"),"{\"sdk\":{\"version\":\"8.0.131\",\"rollForward\":\"disable\"}}");var resolution=NETCoreSdkResolverNativeWrapper.ResolveSdk(root8,jsonDir);Require(Path.GetFileName(resolution.ResolvedSdkDirectory)=="8.0.131","native source SDK resolution");
  for(int i=0;i<16;i++){GC.Collect(2,GCCollectionMode.Forced,true,true);Require(bundle.GetDotnetEnvironmentInfo(root10).RuntimeInfo.Any(r=>r.Version.ToString()=="10.0.5"),"native callback/GC repeat");}
  string missing="{"+Guid.NewGuid().ToString().ToUpperInvariant()+"}";Require(WindowsInstaller.QueryProduct(missing)==InstallState.UNKNOWN,"native MSI missing-product state");Require(!WindowsInstaller.FindRelatedProducts(missing).Any(),"native MSI empty related-product enumeration");Require(WindowsInstaller.GetProductInfo(missing,InstallProperty.INSTALLEDPRODUCTNAME,out _)!=0,"native MSI missing-product error");
  Console.WriteLine("PASS eight original NET10 CLI foundations:owned file/path/sentinel/cache/retry,span parsing/MSBuild forwarding,five shell scripts,upstream/Unicode/invalid manifests,RID alias,source hostfxr SDK/runtime enumeration and resolution,16 compacting-GC callbacks and read-only native MSI errors");
 }
}
