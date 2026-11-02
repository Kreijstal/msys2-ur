using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using NuGet.Commands;
using NuGet.Common;
using NuGet.Configuration;
using NuGet.Frameworks;
using NuGet.LibraryModel;
using NuGet.ProjectModel;
using NuGet.Protocol.Core.Types;
using NuGet.Versioning;
internal static class SupportRestore
{
    static void Require(bool ok,string message){if(!ok)throw new Exception(message);}
    static async Task Main(string[] args)
    {
        string work=args[0],feed=args[1];Directory.CreateDirectory(work);
        string packages=Path.Combine(work,"empty packages 世界"),project=Path.Combine(work,"project.csproj"),config=Path.Combine(work,"NuGet.Config");
        File.WriteAllText(config,"<configuration><packageSources><clear/></packageSources></configuration>");File.WriteAllText(project,"<Project/>");
        var pins=new Dictionary<string,string>{{"System.IO.Hashing","10.0.2"},{"Microsoft.Extensions.DependencyModel","10.0.2"},{"Microsoft.NET.HostModel","10.0.2-servicing.25612.105"},{"Microsoft.Deployment.DotNet.Releases","2.0.0-preview.1.25612.105"}};
        var tfm=NuGetFramework.ParseFolder("net10.0");var sources=new[]{new PackageSource(feed)};
        var fi=new TargetFrameworkInformation{FrameworkName=tfm,TargetAlias="net10.0",Dependencies=pins.Select(p=>new LibraryDependency(new LibraryRange(p.Key,VersionRange.Parse("["+p.Value+"]"),LibraryDependencyTarget.Package))).ToImmutableArray()};
        var spec=new PackageSpec(new[]{fi}){Name="OwnedSdkSupportGraph",FilePath=project,RestoreMetadata=new ProjectRestoreMetadata{ProjectStyle=ProjectStyle.PackageReference,ProjectPath=project,ProjectUniqueName=project,ProjectName="OwnedSdkSupportGraph",OutputPath=Path.Combine(work,"obj"),PackagesPath=packages,Sources=sources,OriginalTargetFrameworks=new[]{"net10.0"},TargetFrameworks=new[]{new ProjectRestoreMetadataFrameworkInfo(tfm){TargetAlias="net10.0"}},ConfigFilePaths=new[]{config},RestoreAuditProperties=new RestoreAuditProperties{EnableAudit="false"}}};
        var graph=new DependencyGraphSpec();graph.AddProject(spec);graph.AddRestore(project);
        using var cache=new SourceCacheContext();var restore=new RestoreArgs{ConfigFile=config,GlobalPackagesFolder=packages,Sources=new List<string>{feed},Log=NullLogger.Instance,CacheContext=cache,DisableParallel=true};
        restore.PreLoadedRequestProviders.Add(new DependencyGraphSpecRequestProvider(new RestoreCommandProvidersCache(),graph,Settings.LoadSpecificSettings(work,"NuGet.Config")));
        var summaries=await RestoreRunner.RunAsync(restore,CancellationToken.None);Require(summaries.Count==1&&summaries[0].Success,"actual SDK support graph restore");
        var file=new LockFileFormat().Read(Path.Combine(work,"obj","project.assets.json"));
        foreach(var pin in pins)
        {
            Require(file.Libraries.Single(l=>l.Name==pin.Key).Version.ToNormalizedString()==pin.Value,"exact SDK support version "+pin.Key);
            string profile=pin.Key=="Microsoft.Deployment.DotNet.Releases"?"netstandard2.0":"net10.0";
            Require(file.Targets.Single().Libraries.Single(l=>l.Name==pin.Key).CompileTimeAssemblies.Any(a=>a.Path=="lib/"+profile+"/"+pin.Key+".dll"),"original compile profile "+pin.Key);
        }
        Require(file.Libraries.Single(l=>l.Name=="System.Text.Json").Version.ToNormalizedString()=="8.0.5","original Releases JSON package version");
        foreach(var library in file.Libraries)Console.WriteLine(library.Name+" "+library.Version.ToNormalizedString());
        Console.WriteLine("PASS four exact SDK10 support packages and transitive source graph: "+file.Libraries.Count+" packages,original NET10/Standard2 assets and JSON8 version");
    }
}
