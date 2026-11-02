using System;
using System.Collections.Immutable;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Xml.Linq;
using Microsoft.CodeAnalysis.Text;
using Microsoft.DotNet.DotNetSdkResolver;
using Microsoft.DotNet.FileBasedPrograms;
using Microsoft.DotNet.ProjectTools;
using Locator = Microsoft.DotNet.TemplateLocator.TemplateLocator;

internal static class Program
{
    static void Require(bool condition,string message) { if(!condition) throw new Exception(message); }
    static void Reject<T>(Action action) where T:Exception { try { action(); } catch(T) { return; } throw new Exception("Expected "+typeof(T).Name); }
    static int Main(string[] args)
    {
        string prefix=Path.GetFullPath(args[0]), source=Path.GetFullPath(args[1]);
        string root=Path.GetFullPath("owned 世界"); Directory.CreateDirectory(root);
        string settingsPath=Path.Combine(root,"preview-settings.txt");
        var settings=new VSSettings(settingsPath,true);
        Require(settings.DisallowPrerelease(),"Missing settings default");
        File.WriteAllText(settingsPath,"UsePreviews=true\n");
        Require(!settings.DisallowPrerelease(),"Enable previews");
        File.WriteAllText(settingsPath,"UsePreviews=false\n"); File.SetLastWriteTimeUtc(settingsPath,DateTime.UtcNow.AddSeconds(10));
        Parallel.For(0,32,_=>Require(settings.DisallowPrerelease(),"Concurrent refreshed settings"));
        File.Delete(settingsPath);Require(settings.DisallowPrerelease(),"Deleted settings default");
        string dotnet8=Path.Combine(prefix,"lib","dotnet");
        string? GetEnv(string name) => name=="DOTNET_MSBUILD_SDK_RESOLVER_CLI_DIR" ? dotnet8 : name=="PATH" ? "" : null;
        var resolver=new NETCoreSdkResolver(GetEnv,settings);
        string sdkFixture=Path.Combine(root,"sdk-version-fixture");Directory.CreateDirectory(sdkFixture);
        Require(resolver.GetMinimumMSBuildVersion(sdkFixture)==new Version(15,3,0),"Legacy minimum MSBuild");
        string explicitFixture=Path.Combine(root,"explicit-version");Directory.CreateDirectory(explicitFixture);
        File.WriteAllText(Path.Combine(explicitFixture,"minimumMSBuildVersion"),"18.3.0\n");
        Require(resolver.GetMinimumMSBuildVersion(explicitFixture)==new Version(18,3,0),"Explicit minimum MSBuild");
        string sdkSelection=Path.Combine(root,"sdk-selection");Directory.CreateDirectory(sdkSelection);
        File.WriteAllText(Path.Combine(sdkSelection,"global.json"),"{\"sdk\":{\"version\":\"8.0.131\",\"rollForward\":\"disable\"}}");
        var result=resolver.ResolveNETCoreSdkDirectory(sdkSelection,new Version(18,3,0),false,dotnet8);
        Require(result.ResolvedSdkDirectory!=null && Path.GetFileName(result.ResolvedSdkDirectory)=="8.0.131","Native hostfxr pinned SDK resolution");
        Require(result.GlobalJsonPath==Path.Combine(sdkSelection,"global.json"),"Native global.json provenance");
        Console.WriteLine("PASS resolver settings cache/default/concurrency, MSBuild minimum versions and native global.json SDK selection");
        var locator=new Locator(GetEnv,()=>Path.Combine(dotnet8,"dotnet.exe"),settings,null,null);
        Require(locator.TryGetDotnetSdkVersionUsedInVs("18.3",out var selected) && selected=="8.0.131","VS SDK selection");
        Reject<ArgumentException>(()=>locator.TryGetDotnetSdkVersionUsedInVs("invalid",out _));
        Reject<ArgumentException>(()=>locator.GetDotnetSdkTemplatePackages(" ",root,null));
        string fakeRoot=Path.Combine(root,"template-root");
        string sdkPath=Path.Combine(fakeRoot,"sdk","5.0.102");Directory.CreateDirectory(sdkPath);
        File.WriteAllLines(Path.Combine(sdkPath,"NETCoreSdkRuntimeIdentifierChain.txt"),new[]{"win-x64","win","any","base"});
        string manifests=Path.Combine(fakeRoot,"sdk-manifests","5.0.100","Android");Directory.CreateDirectory(manifests);
        File.Copy(Path.Combine(source,"test","Microsoft.DotNet.TemplateLocator.Tests","Manifests","AndroidWorkloadManifest.json"),Path.Combine(manifests,"WorkloadManifest.json"));
        string packs=Path.Combine(fakeRoot,"template-packs");Directory.CreateDirectory(packs);
        string package=Path.Combine(packs,"xamarin.android.templates.1.0.3.nupkg");File.WriteAllText(package,"");
        var templates=locator.GetDotnetSdkTemplatePackages("5.0.102",fakeRoot,null);
        Require(templates.Count==1,"One installed template");var template=templates.Single();
        Require(template.TemplatePackageId=="Xamarin.Android.Templates" && template.TemplateVersion=="1.0.3" && template.Path==package,"Original upstream template fixture identity/path");
        var emptyLocator=new Locator(GetEnv,null,settings,null,null);
        Require(emptyLocator.GetDotnetSdkTemplatePackages("5.0.102",Path.Combine(root,"absent-root"),null).Count==0,"No manifests gives no templates");
        Console.WriteLine("PASS template locator native VS SDK selection, original upstream workload fixture, installed-template filtering and invalid/missing cases");
        string app=Path.Combine(root,"hello 世界.cs");
        const string body="Console.WriteLine(\"Hello 世界\");\n";
        File.WriteAllText(app,"#!/usr/bin/env dotnet\n#:sdk Microsoft.NET.Sdk\n#:property TargetFramework=net10.0\n#:property Description=Hello & 世界\n#:package Example.Library@1.2.3\n#:project ./dependency.csproj\n"+body,new UTF8Encoding(false));
        var reporter=ErrorReporters.CreateCollectingReporter(out var diagnostics);
        var file=SourceFile.Load(app);var directives=FileLevelDirectiveHelpers.FindDirectives(file,true,reporter);
        Require(diagnostics.Count==0,"Valid directives: "+string.Join(";",diagnostics.Select(d=>d.Message)));
        Require(directives.OfType<CSharpDirective.Package>().Single().Version=="1.2.3","Original Roslyn directive parser package");
        var defaults=VirtualProjectBuilder.GetDefaultProperties("10.0").ToArray();
        Require(defaults.Contains(("PublishAot","true")) && defaults.Contains(("PackAsTool","true")),"Original file-app publish defaults");
        foreach(bool isVirtual in new[]{false,true})
        {
            using var writer=new StringWriter();
            VirtualProjectBuilder.WriteProjectFile(writer,directives,defaults,isVirtual,app,Path.Combine(root,"artifacts 世界"));
            var xml=XDocument.Parse(writer.ToString());
            Require(xml.Descendants("Description").Single().Value=="Hello & 世界","XML escaping");
            Require(xml.Descendants("TargetFramework").Last().Value=="net10.0","Original target framework");
            var reference=xml.Descendants("PackageReference").Single();
            Require((string?)reference.Attribute("Include")=="Example.Library" && (string?)reference.Attribute("Version")=="1.2.3","Package reference generation");
            Require((string?)xml.Descendants("ProjectReference").Single().Attribute("Include")=="./dependency.csproj","Project reference generation");
            Require(xml.Descendants("PublishAot").Single().Value=="true","Preserve AOT default");
        }
        var stripped=VirtualProjectBuilder.RemoveDirectivesFromFile(directives,file.Text);
        Require(stripped!=null && stripped.ToString().Contains(body) && !stripped.ToString().Contains("#:package"),"Directive removal preserves C# body");
        Require(VirtualProjectBuilder.IsValidEntryPointPath(app),"C# entry point");
        string script=Path.Combine(root,"run-script");File.WriteAllText(script,"#!/usr/bin/env dotnet\n"+body);
        Require(VirtualProjectBuilder.IsValidEntryPointPath(script),"Shebang entry point");
        File.WriteAllText(script,"ordinary text");Require(!VirtualProjectBuilder.IsValidEntryPointPath(script),"Reject non-C# non-shebang");
        var invalid=new SourceFile(app,SourceText.From("#:package Bad@1\n#:package Bad@2\n"+body));
        FileLevelDirectiveHelpers.FindDirectives(invalid,true,reporter);Require(diagnostics.Count>0,"Duplicate directive diagnostic");
        string projectDir=Path.Combine(root,"projects");Directory.CreateDirectory(projectDir);
        Require(!ProjectLocator.TryGetProjectFileFromDirectory(projectDir,out _,out var error) && !string.IsNullOrWhiteSpace(error),"Empty project directory error");
        string project=Path.Combine(projectDir,"one.csproj");File.WriteAllText(project,"<Project/>");
        Require(ProjectLocator.TryGetProjectFileFromDirectory(projectDir,out var found,out _) && found==project,"One project selection");
        File.WriteAllText(Path.Combine(projectDir,"two.csproj"),"<Project/>");Require(!ProjectLocator.TryGetProjectFileFromDirectory(projectDir,out _,out error) && !string.IsNullOrWhiteSpace(error),"Ambiguous project error");
        Console.WriteLine("PASS signed friend consumer, original Roslyn file directives/errors, Unicode project generation/removal, AOT defaults, entry point and project selection");
        return 0;
    }
}
