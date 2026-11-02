using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.TemplateEngine.Abstractions;
using Microsoft.TemplateEngine.Abstractions.Installer;
using Microsoft.TemplateEngine.Edge;
using Microsoft.TemplateEngine.Edge.Settings;
using Microsoft.TemplateEngine.Edge.Template;
using Microsoft.TemplateSearch.Common;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

internal static class Check
{
    internal static void Require(bool ok,string message) {if(!ok)throw new Exception(message);}
    static async Task<int> Main(string[] args)
    {
        string refs=args[0],baselines=args[1],work=args[2];
        string[] names={"Microsoft.TemplateEngine.Abstractions","Microsoft.TemplateEngine.Core.Contracts","Microsoft.TemplateEngine.Utils","Microsoft.TemplateEngine.Core","Microsoft.TemplateEngine.Orchestrator.RunnableProjects","Microsoft.TemplateEngine.Edge","Microsoft.TemplateSearch.Common"};
        var framework=Directory.GetFiles(refs,"*.dll").Select(p=>MetadataReference.CreateFromFile(p));
        var extra=Directory.GetFiles(AppContext.BaseDirectory,"*.dll").Where(p=>!new[]{"Check","Microsoft.CodeAnalysis","Microsoft.CodeAnalysis.CSharp"}.Contains(Path.GetFileNameWithoutExtension(p)) && !Directory.GetFiles(refs,"*.dll").Any(r=>Path.GetFileName(r)==Path.GetFileName(p))).ToArray();
        int apiFailures=0;bool runtimeOnly=args.Length>3 && args[3]=="runtime-only";
        foreach(var name in names)
        {
            var assembly=Assembly.Load(name);Require(assembly.GetName().Version!.ToString()=="10.0.200.0",name+" assembly identity");
            Require(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>()!.Version=="10.2.26.11413",name+" file version");
            Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="adb9793829ddae60",name+" original key");
            Require(assembly.GetCustomAttribute<System.Runtime.Versioning.TargetFrameworkAttribute>()!.FrameworkName==".NETCoreApp,Version=v10.0",name+" original profile");
            if(!runtimeOnly)
            {
                try {CheckApi.Run(framework,assembly.Location,Path.Combine(baselines,name+".txt"),extra.Where(p=>Path.GetFileNameWithoutExtension(p)!=name).ToArray());}
                catch(Exception error) when(error.Message.Contains("upstream API declarations missing")) {apiFailures++;}
            }
        }
        if(args.Length>3 && args[3]=="api") return apiFailures==0 ? 0:1;
        Directory.CreateDirectory(work);
        string policy=Path.Combine(work,"api-policy.txt");
        File.WriteAllText(policy,"~static ApiGateFixture.Echo(string value) -> string\n");
        CheckApi.Run(framework,typeof(ApiGateFixture).Assembly.Location,policy,extra);
        File.WriteAllText(policy,"static ApiGateFixture.Echo(string? value) -> string!\n");
        bool nullableMismatchRejected=false;
        try {CheckApi.Run(framework,typeof(ApiGateFixture).Assembly.Location,policy,extra);}
        catch(Exception error) when(error.Message.Contains("upstream API declarations missing")) {nullableMismatchRejected=true;}
        Require(nullableMismatchRejected,"annotated baseline nullable changes must fail");
        string input=Path.Combine(work,"template 世界"),config=Path.Combine(input,".template.config");Directory.CreateDirectory(config);
        File.WriteAllText(Path.Combine(config,"template.json"),"""
        {"identity":"Owned.Source.Template","name":"Owned template 世界","shortName":"owned-port","sourceName":"OwnedTemplate","preferNameDirectory":false,
         "symbols":{"greeting":{"type":"parameter","datatype":"string","defaultValue":"Hello","replaces":"GREETING_TOKEN"},"feature":{"type":"parameter","datatype":"bool","defaultValue":"true"},"derivedFeature":{"type":"computed","datatype":"bool","value":"gate"},"gate":{"type":"computed","datatype":"bool","value":"feature && true"}}}
        """);
        File.WriteAllText(Path.Combine(input,"OwnedTemplate.csproj"),"<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net10.0</TargetFramework><RootNamespace>OwnedTemplate</RootNamespace></PropertyGroup></Project>");
        File.WriteAllText(Path.Combine(input,"Program.cs"),"namespace OwnedTemplate;\n// GREETING_TOKEN\n//#if (derivedFeature)\n// included-feature\n//#else\n// excluded-feature\n//#endif\n");
        var builtins=Microsoft.TemplateEngine.Edge.Components.AllComponents.Concat(Microsoft.TemplateEngine.Orchestrator.RunnableProjects.Components.AllComponents).ToArray();
        var host=new DefaultTemplateEngineHost("owned-source-check","1.0.0",builtIns:builtins);using var environment=new EngineEnvironmentSettings(host,settingsLocation:Path.Combine(work,"settings"));
        var scanner=new Scanner(environment);using var scan=await scanner.ScanAsync(input);var scanned=scan.Templates.Single(t=>t.Identity=="Owned.Source.Template");
        using var manager=new TemplatePackageManager(environment);var provider=manager.GetBuiltInManagedProvider();
        var installed=await provider.InstallAsync(new[]{new InstallRequest(input)},CancellationToken.None);Require(installed.Single().Success,"owned folder package install");
        var template=(await manager.GetTemplatesAsync(CancellationToken.None)).Single(t=>t.Identity==scanned.Identity);
        Require(template.Name=="Owned template 世界","scan Unicode template metadata");
        var search=new TemplateSearchData(template);var serialized=JObject.Parse(JsonConvert.SerializeObject(search));Require((string?)serialized["Identity"]==template.Identity && (string?)serialized["Name"]==template.Name,"search metadata JSON serializer");
        var creator=new TemplateCreator(environment);string dry=Path.Combine(work,"dry-run");
        var preview=await creator.InstantiateAsync(template,"OwnedDry","OwnedDry",dry,new Dictionary<string,string?> { ["greeting"]="Grüße 世界",["feature"]="true" },dryRun:true);
        Require(preview.Status==CreationResultStatus.Success && !File.Exists(Path.Combine(dry,"Program.cs")),"dry run without generated files: "+preview.ErrorMessage);
        foreach(bool feature in new[]{true,false})
        {
            string output=Path.Combine(work,"generated-"+feature),name="OwnedApp"+feature;
            var result=await creator.InstantiateAsync(template,name,name,output,new Dictionary<string,string?> { ["greeting"]="Grüße 世界",["feature"]=feature.ToString() });
            Require(result.Status==CreationResultStatus.Success,"template creation: "+result.ErrorMessage);
            string code=File.ReadAllText(Path.Combine(output,"Program.cs"));
            Require(code.Contains("namespace "+name+";") && code.Contains("Grüße 世界"),"name and Unicode parameter replacement");
            Require(code.Contains(feature ? "included-feature":"excluded-feature") && !code.Contains(feature ? "excluded-feature":"included-feature"),"conditional content");
            Require(File.Exists(Path.Combine(output,name+".csproj")) && !Directory.Exists(Path.Combine(output,".template.config")),"file rename and config exclusion");
        }
        bool cancelled=false;try{using var ignored=await scanner.ScanAsync(input,cancellationToken:new CancellationToken(true));}catch(OperationCanceledException){cancelled=true;}Require(cancelled,"scan cancellation");
        var managed=await manager.GetManagedTemplatePackagesAsync(false,CancellationToken.None);var removed=await provider.UninstallAsync(managed,CancellationToken.None);Require(removed.All(r=>r.Success),"owned folder package uninstall");
        Require(!(await manager.GetManagedTemplatePackagesAsync(false,CancellationToken.None)).Any(),"folder package removal reflected in settings");
        var packageBuilder=new NuGet.Packaging.PackageBuilder {Id="Owned.Source.TemplatePackage",Version=NuGet.Versioning.NuGetVersion.Parse("1.0.0"),Description="Owned source TemplateEngine integration fixture"};
        packageBuilder.Authors.Add("Owned fixture");
        foreach(string file in Directory.EnumerateFiles(input,"*",SearchOption.AllDirectories))
            packageBuilder.Files.Add(new NuGet.Packaging.PhysicalPackageFile {SourcePath=file,TargetPath="content/"+Path.GetRelativePath(input,file).Replace('\\','/')});
        string packagePath=Path.Combine(work,"Owned.Source.TemplatePackage.1.0.0.nupkg");
        using(var stream=File.Create(packagePath))packageBuilder.Save(stream);
        var packageInstall=await provider.InstallAsync(new[]{new InstallRequest(packagePath)},CancellationToken.None);
        Require(packageInstall.Count==1 && packageInstall[0].Success,"local NuGet template package install: "+packageInstall[0].ErrorMessage);
        var nugetPackage=packageInstall[0].TemplatePackage!;
        Require(nugetPackage.Identifier=="Owned.Source.TemplatePackage" && nugetPackage.Version=="1.0.0" && nugetPackage.Installer.Factory.Name=="NuGet","actual NuGet installer identity/version");
        var packagedTemplate=(await manager.GetTemplatesAsync(CancellationToken.None)).Single(t=>t.Identity=="Owned.Source.Template");
        string packageOutput=Path.Combine(work,"from-package");
        var packageResult=await creator.InstantiateAsync(packagedTemplate,"OwnedNuGet","OwnedNuGet",packageOutput,new Dictionary<string,string?> {["greeting"]="NuGet Grüße 世界",["feature"]="true"});
        Require(packageResult.Status==CreationResultStatus.Success,"NuGet template instantiation: "+packageResult.ErrorMessage);
        string packagedCode=File.ReadAllText(Path.Combine(packageOutput,"Program.cs"));
        Require(packagedCode.Contains("namespace OwnedNuGet;") && packagedCode.Contains("NuGet Grüße 世界") && packagedCode.Contains("included-feature"),"NuGet template generation and dependency-ordered macros");
        var packageRemoval=await provider.UninstallAsync(await manager.GetManagedTemplatePackagesAsync(false,CancellationToken.None),CancellationToken.None);
        Require(packageRemoval.Count==1 && packageRemoval[0].Success && !(await manager.GetManagedTemplatePackagesAsync(false,CancellationToken.None)).Any(),"NuGet template uninstall and settings cleanup");
        Console.WriteLine("PASS original TemplateEngine seven-library identities; owned Unicode scan/search JSON; dry run; file/name/parameter replacement; conditional generation; config exclusion, dependency-ordered computed macros, cancellation and actual NuGet package install/generation/uninstall");
        return 0;
    }
}

public static class ApiGateFixture {public static string Echo(string value)=>value;}
