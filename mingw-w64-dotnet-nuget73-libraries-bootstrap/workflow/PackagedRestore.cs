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
internal static class PackagedRestore
{
    static void Require(bool ok,string message){if(!ok)throw new Exception(message);}
    static async Task Main(string[] args)
    {
        string work=args[0],candidate=args[1],installed=args[2];Directory.CreateDirectory(work);
        string packages=Path.Combine(work,"empty packages 世界"),project=Path.Combine(work,"project.csproj"),config=Path.Combine(work,"NuGet.Config");
        File.WriteAllText(config,"<configuration><packageSources><clear/></packageSources></configuration>");File.WriteAllText(project,"<Project/>");
        var tfm=NuGetFramework.ParseFolder("net10.0");string version="7.3.0-preview.1.11413";
        string[] names={"NuGet.Configuration","NuGet.Packaging","NuGet.Protocol","NuGet.DependencyResolver.Core","NuGet.ProjectModel","NuGet.Credentials","NuGet.Resolver","NuGet.Commands"};
        var sources=new[]{new PackageSource(candidate),new PackageSource(installed)}.DistinctBy(p=>p.Source).ToArray();
        var fi=new TargetFrameworkInformation{FrameworkName=tfm,TargetAlias="net10.0",Dependencies=names.Select(n=>new LibraryDependency(new LibraryRange(n,VersionRange.Parse("["+version+"]"),LibraryDependencyTarget.Package))).ToImmutableArray()};
        var spec=new PackageSpec(new[]{fi}){Name="OwnedPackageGraph",FilePath=project,RestoreMetadata=new ProjectRestoreMetadata{ProjectStyle=ProjectStyle.PackageReference,ProjectPath=project,ProjectUniqueName=project,ProjectName="OwnedPackageGraph",OutputPath=Path.Combine(work,"obj"),PackagesPath=packages,Sources=sources,OriginalTargetFrameworks=new[]{"net10.0"},TargetFrameworks=new[]{new ProjectRestoreMetadataFrameworkInfo(tfm){TargetAlias="net10.0"}},ConfigFilePaths=new[]{config},RestoreAuditProperties=new RestoreAuditProperties{EnableAudit="false"}}};
        var graph=new DependencyGraphSpec();graph.AddProject(spec);graph.AddRestore(project);
        using var cache=new SourceCacheContext();var restore=new RestoreArgs{ConfigFile=config,GlobalPackagesFolder=packages,Sources=sources.Select(p=>p.Source).ToList(),Log=NullLogger.Instance,CacheContext=cache,DisableParallel=true};
        restore.PreLoadedRequestProviders.Add(new DependencyGraphSpecRequestProvider(new RestoreCommandProvidersCache(),graph,Settings.LoadSpecificSettings(work,"NuGet.Config")));
        var summaries=await RestoreRunner.RunAsync(restore,CancellationToken.None);Require(summaries.Count==1&&summaries[0].Success,"actual eight-package source graph restore");
        var file=new LockFileFormat().Read(Path.Combine(work,"obj","project.assets.json"));
        foreach(var name in names.Concat(new[]{"NuGet.Versioning","NuGet.Frameworks","NuGet.Common","NuGet.LibraryModel"}))
        {Require(file.Libraries.Single(l=>l.Name==name).Version.ToNormalizedString()==version,"exact source NuGet version "+name);Require(file.Targets.Single().Libraries.Single(l=>l.Name==name).CompileTimeAssemblies.Any(a=>a.Path=="lib/net10.0/"+name+".dll"),"original NET10 compile asset "+name);}
        foreach(var expected in new[]{("Newtonsoft.Json","13.0.3"),("System.Security.Cryptography.Pkcs","8.0.1"),("System.Security.Cryptography.ProtectedData","8.0.0"),("Microsoft.Extensions.FileSystemGlobbing","6.0.0"),("Microsoft.Extensions.FileProviders.Abstractions","6.0.0"),("Microsoft.Extensions.Primitives","6.0.0")})
            Require(file.Libraries.Single(l=>l.Name==expected.Item1).Version.ToNormalizedString()==expected.Item2,"exact declared external dependency "+expected.Item1);
        foreach(var library in file.Libraries)Console.WriteLine(library.Name+" "+library.Version.ToNormalizedString());
        Console.WriteLine("PASS actual eight packaged NuGet7.3 libraries and transitive source dependency graph: "+file.Libraries.Count+" packages; original NET10 assets and exact external versions");
    }
}
