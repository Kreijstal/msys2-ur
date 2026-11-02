using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using NuGet.Commands;
using NuGet.Common;
using NuGet.Configuration;
using NuGet.Frameworks;
using NuGet.LibraryModel;
using NuGet.Packaging;
using NuGet.Packaging.Core;
using NuGet.ProjectModel;
using NuGet.Protocol;
using NuGet.Protocol.Core.Types;
using NuGet.Versioning;

static class Program
{
    static void Require(bool condition,string message) { if(!condition) throw new Exception(message); }
    static void Package(string directory,string feed,string name,string version,bool dependency)
    {
        string path=Path.Combine(directory,name+"."+version+".txt");
        File.WriteAllText(path,name+" "+version+" λ owned");
        var builder=new PackageBuilder { Id=name,Version=NuGetVersion.Parse(version),Description="Owned source NuGet fixture" };
        builder.Authors.Add("Owned fixture");
        builder.Files.Add(new PhysicalPackageFile { SourcePath=path,TargetPath="content/λ.txt" });
        if(dependency) builder.DependencyGroups.Add(new PackageDependencyGroup(NuGetFramework.AnyFramework,new[] {
            new PackageDependency("Owned.Dependency",VersionRange.Parse("[1.0.0]")) }));
        using var output=File.Create(Path.Combine(feed,name+"."+version+".nupkg"));builder.Save(output);
    }
    static async Task Main(string[] args)
    {
        string directory=Path.GetFullPath(args[0]);Directory.CreateDirectory(directory);
        string feed=Path.Combine(directory,"feed");Directory.CreateDirectory(feed);
        Package(directory,feed,"Owned.Dependency","1.0.0",false);
        Package(directory,feed,"Owned.Root","1.0.0",true);
        Package(directory,feed,"Owned.Root","1.1.0-preview.1",true);
        var range=VersionRange.Parse("[1.0.0,2.0.0)");
        Require(range.Satisfies(NuGetVersion.Parse("1.5.0")) && !range.Satisfies(NuGetVersion.Parse("2.0.0")),"version range boundaries");
        var repository=Repository.Factory.GetCoreV3(feed);
        using var cache=new SourceCacheContext { NoCache=true };
        var resource=await repository.GetResourceAsync<FindPackageByIdResource>();
        var versions=(await resource.GetAllVersionsAsync("Owned.Root",cache,NullLogger.Instance,CancellationToken.None)).ToArray();
        Require(versions.Length==2 && versions.Any(version=>version.ToNormalizedString()=="1.1.0-preview.1"),"local stable/prerelease protocol discovery");
        using var copy=new MemoryStream();
        Require(await resource.CopyNupkgToStreamAsync("Owned.Root",NuGetVersion.Parse("1.0.0"),copy,cache,NullLogger.Instance,CancellationToken.None),"local protocol package copy");
        copy.Position=0;
        using(var reader=new PackageArchiveReader(copy,true))
        {
            Require(reader.GetIdentity().Id=="Owned.Root","package identity");
            using var payload=new StreamReader(reader.GetStream("content/λ.txt"));
            Require(payload.ReadToEnd()=="Owned.Root 1.0.0 λ owned","Unicode package payload");
        }
        Console.WriteLine("PASS source NuGet package builder/archive, version ranges and local stable/prerelease protocol discovery/download");

        string project=Path.Combine(directory,"Owned.Consumer.csproj");
        string packages=Path.Combine(directory,"packages");string output=Path.Combine(directory,"obj");
        string config=Path.Combine(directory,"NuGet.config");
        File.WriteAllText(config,"<configuration><packageSources><clear/><add key=\"owned\" value=\""+System.Security.SecurityElement.Escape(feed)+"\"/></packageSources></configuration>");
        var framework=NuGetFramework.ParseFolder("net8.0");
        var spec=new PackageSpec(new[] { new TargetFrameworkInformation { FrameworkName=framework } }) {
            Name="Owned.Consumer",Version=new NuGetVersion("1.0.0"),FilePath=project,
            RestoreMetadata=new ProjectRestoreMetadata { ProjectStyle=ProjectStyle.PackageReference,ProjectPath=project,
                ProjectUniqueName=project,ProjectName="Owned.Consumer",OutputPath=output,PackagesPath=packages,
                OriginalTargetFrameworks=new List<string> { "net8.0" },ConfigFilePaths=new List<string> { config },
                Sources=new List<PackageSource> { new PackageSource(feed) },
                TargetFrameworks=new List<ProjectRestoreMetadataFrameworkInfo> { new ProjectRestoreMetadataFrameworkInfo(framework) } }
        };
        spec.Dependencies.Add(new LibraryDependency { LibraryRange=new LibraryRange("Owned.Root",VersionRange.Parse("[1.0.0]"),LibraryDependencyTarget.Package) });
        var graph=new DependencyGraphSpec();graph.AddProject(spec);graph.AddRestore(project);
        var settings=Settings.LoadSpecificSettings(directory,"NuGet.config");
        var restore=new RestoreArgs { CacheContext=cache,DisableParallel=true,GlobalPackagesFolder=packages,
            ConfigFile=config,Sources=new List<string> { feed },Log=NullLogger.Instance,
            CachingSourceProvider=new CachingSourceProvider(new PackageSourceProvider(settings)),
            PreLoadedRequestProviders=new List<IPreLoadedRestoreRequestProvider> {
                new DependencyGraphSpecRequestProvider(new RestoreCommandProvidersCache(),graph) } };
        var summaries=await RestoreRunner.RunAsync(restore);
        Require(summaries.Count==1 && summaries[0].Success,"original RestoreRunner dependency graph restore");
        var assets=new LockFileFormat().Read(Path.Combine(output,"project.assets.json"));
        Require(assets.Libraries.Any(item=>item.Name=="Owned.Root") && assets.Libraries.Any(item=>item.Name=="Owned.Dependency"),"assets dependency closure");
        foreach(string name in new[] { "owned.root","owned.dependency" })
            Require(File.ReadAllText(Path.Combine(packages,name,"1.0.0","content","λ.txt")).EndsWith("1.0.0 λ owned"),"installed payload "+name);
        foreach(var assembly in AppDomain.CurrentDomain.GetAssemblies().Where(assembly=>assembly.GetName().Name.StartsWith("NuGet.",StringComparison.Ordinal)))
            Require(assembly.GetName().Version.ToString()=="6.9.1.3" && Path.GetDirectoryName(assembly.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"foreign NuGet implementation "+assembly.FullName);
        Console.WriteLine("PASS original source NuGet.Commands RestoreRunner, complete dependency resolution, owned global cache/assets and Unicode extraction");
        await ProtocolChecks.Run(feed);
        await SigningChecks.Run(directory,Path.Combine(feed,"Owned.Root.1.0.0.nupkg"));
    }
}
