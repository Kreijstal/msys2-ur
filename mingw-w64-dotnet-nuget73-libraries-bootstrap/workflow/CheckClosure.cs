using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Resources;
using System.Runtime.Versioning;
using System.Threading;
using System.Threading.Tasks;
using System.Text.Json;
using System.Xml;
using System.Xml.Linq;
using Microsoft.CodeAnalysis;
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

internal static class Check
{
    internal static void Require(bool ok,string message) {if(!ok)throw new Exception(message);}
    static async Task Main(string[] args)
    {
        string source=args[0],refs=args[1],baselines=args[2],work=args[3];
        string[] names={"NuGet.Configuration","NuGet.Packaging","NuGet.Protocol","NuGet.DependencyResolver.Core","NuGet.ProjectModel","NuGet.Credentials","NuGet.Resolver","NuGet.Commands"};
        var framework=Directory.GetFiles(refs,"*.dll").Select(p=>MetadataReference.CreateFromFile(p)).ToArray();
        int strings=0,api=0;
        foreach(var name in names)
        {
            var a=Assembly.Load(name);var n=a.GetName();
            Require(n.Version!.ToString()=="7.3.0.0"&&Convert.ToHexString(n.GetPublicKeyToken()!).ToLowerInvariant()=="31bf3856ad364e35","identity "+name);
            Require(a.GetCustomAttribute<TargetFrameworkAttribute>()!.FrameworkName==".NETCoreApp,Version=v10.0","original VMR framework "+name);
            Require(a.GetCustomAttribute<AssemblyFileVersionAttribute>()!.Version=="7.3.0.11413","file version "+name);
            using(var peFile=File.OpenRead(a.Location))
            using(var pe=new PEReader(peFile))
            using(var pdbFile=File.OpenRead(Path.ChangeExtension(a.Location,".pdb")))
            using(var provider=MetadataReaderProvider.FromPortablePdbStream(pdbFile))
            {
                var debug=pe.ReadDebugDirectory().Single(e=>e.Type==DebugDirectoryEntryType.CodeView);
                var codeView=pe.ReadCodeViewDebugDirectoryData(debug);var id=new BlobContentId(provider.GetMetadataReader().DebugMetadataHeader!.Id);
                Require(codeView.Guid==id.Guid&&debug.Stamp==id.Stamp,"matching original portable PDB "+name);
            }
            string baseline=Path.Combine(baselines,name+".txt");
            CheckApi.Run(framework,a.Location,baseline,Directory.GetFiles(AppContext.BaseDirectory,"*.dll").Where(p=>Path.GetFileName(p)!=name+".dll"&&Path.GetFileName(p)!="Check.dll").ToArray());
            api+=File.ReadLines(baseline).Count(l=>!string.IsNullOrWhiteSpace(l)&&!l.StartsWith("#")&&!l.StartsWith("*REMOVED*"));
            foreach(var resx in Directory.GetFiles(Path.Combine(source,"src/NuGet.Core",name),"*.resx"))
            {
                string logical=name+"."+Path.GetFileNameWithoutExtension(resx)+".resources";
                using var set=new ResourceSet(a.GetManifestResourceStream(logical)!);
                using var reader=new XmlTextReader(resx);reader.WhitespaceHandling=WhitespaceHandling.All;
                foreach(var data in XDocument.Load(reader,LoadOptions.PreserveWhitespace).Root!.Elements("data"))
                {Require(set.GetString(data.Attribute("name")!.Value)==data.Element("value")!.Value,"resource "+logical);strings++;}
            }
        }
        if(args.Length>4)
        {
            using var localized=JsonDocument.Parse(File.ReadAllText(args[4]));
            foreach(var item in localized.RootElement.EnumerateArray())
            {
                var a=Assembly.Load(item.GetProperty("assembly").GetString()!);
                var culture=CultureInfo.GetCultureInfo(item.GetProperty("culture").GetString()!);var sat=a.GetSatelliteAssembly(culture);
                Require(sat.GetName().Version!.ToString()=="7.3.0.0"&&Convert.ToHexString(sat.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="31bf3856ad364e35","satellite identity");
                string logical=item.GetProperty("resource").GetString()!;using var set=new ResourceSet(sat.GetManifestResourceStream(logical+"."+culture.Name+".resources")!);var manager=new ResourceManager(logical,a);
                foreach(var value in item.GetProperty("strings").EnumerateObject())
                {Require(set.GetString(value.Name)==value.Value.GetString()&&manager.GetString(value.Name,culture)==value.Value.GetString(),"localized value "+logical+"/"+culture+"/"+value.Name);strings++;}
            }
        }
        Require(typeof(PackageBuilder).Assembly.GetManifestResourceNames().Contains("NuGet.Packaging.nuspec.xsd"),"original linked nuspec schema");
        Directory.CreateDirectory(work);string feed=Path.Combine(work,"feed 世界"),packages=Path.Combine(work,"packages"),project=Path.Combine(work,"project 世界");
        Directory.CreateDirectory(feed);Directory.CreateDirectory(project);
        string config=Path.Combine(work,"NuGet.Config");File.WriteAllText(config,"<configuration><packageSources><clear/></packageSources><config><add key=\"globalPackagesFolder\" value=\""+packages+"\"/></config></configuration>");
        var settings=Settings.LoadSpecificSettings(work,"NuGet.Config");
        settings.AddOrUpdate("packageSources",new SourceItem("owned",feed));settings.SaveToDisk();
        var reloaded=Settings.LoadSpecificSettings(work,"NuGet.Config");
        Require(Path.GetFullPath(new PackageSourceProvider(reloaded).LoadPackageSources().Single().Source)==Path.GetFullPath(feed),"owned config roundtrip");
        string secret="synthetic Grüsse 世界 "+Guid.NewGuid();string encrypted=EncryptionUtility.EncryptString(secret);
        Require(encrypted!=secret&&EncryptionUtility.DecryptString(encrypted)==secret,"current-user DPAPI roundtrip");
        string content=Path.Combine(work,"_._");File.WriteAllText(content,"");var tfm=NuGetFramework.ParseFolder("net10.0");
        foreach(var id in new[]{"Owned.Dependency","Owned.Root"})
        {
            var builder=new PackageBuilder{Id=id,Version=NuGetVersion.Parse("1.0.0"),Description="Owned offline source NuGet73 integration fixture"};builder.Authors.Add("source-test");
            builder.Files.Add(new PhysicalPackageFile{SourcePath=content,TargetPath="lib/net10.0/_._"});
            if(id=="Owned.Root")builder.DependencyGroups.Add(new PackageDependencyGroup(tfm,new[]{new PackageDependency("Owned.Dependency",VersionRange.Parse("[1.0.0]"))}));
            string path=Path.Combine(feed,id+".1.0.0.nupkg");using(var output=File.Create(path))builder.Save(output);
            using var reader=new PackageArchiveReader(path);Require(reader.GetIdentity().Id==id&&reader.GetFiles().Contains("lib/net10.0/_._"),"pack/schema/archive "+id);
        }
        using var cache=new SourceCacheContext();var repository=Repository.Factory.GetCoreV3(feed);
        var resource=await repository.GetResourceAsync<FindPackageByIdResource>();
        var versions=(await resource.GetAllVersionsAsync("Owned.Root",cache,NullLogger.Instance,CancellationToken.None)).ToArray();
        Require(versions.Length==1&&versions[0].ToNormalizedString()=="1.0.0","local protocol package lookup");
        string pathProject=Path.Combine(project,"owned.csproj");File.WriteAllText(pathProject,"<Project/>");
        var frameworkInfo=new TargetFrameworkInformation{FrameworkName=tfm,TargetAlias="net10.0",Dependencies=ImmutableArray.Create(new LibraryDependency(new LibraryRange("Owned.Root",VersionRange.Parse("[1.0.0]"),LibraryDependencyTarget.Package)))};
        var spec=new PackageSpec(new[]{frameworkInfo}){Name="OwnedProject",FilePath=pathProject,RestoreMetadata=new ProjectRestoreMetadata{ProjectStyle=ProjectStyle.PackageReference,ProjectPath=pathProject,ProjectUniqueName=pathProject,ProjectName="OwnedProject",OutputPath=Path.Combine(project,"obj"),PackagesPath=packages,Sources=new[]{new PackageSource(feed)},OriginalTargetFrameworks=new[]{"net10.0"},TargetFrameworks=new[]{new ProjectRestoreMetadataFrameworkInfo(tfm){TargetAlias="net10.0"}},ConfigFilePaths=new[]{config},RestoreAuditProperties=new RestoreAuditProperties{EnableAudit="false"}}};
        var graph=new DependencyGraphSpec();graph.AddProject(spec);graph.AddRestore(pathProject);string graphFile=Path.Combine(project,"owned.dg.json");graph.Save(graphFile);
        var restoredGraph=DependencyGraphSpec.Load(graphFile);Require(restoredGraph.Projects.Count==1,"dependency graph JSON roundtrip");
        var restoreArgs=new RestoreArgs{ConfigFile=config,GlobalPackagesFolder=packages,Sources=new List<string>{feed},Log=NullLogger.Instance,CacheContext=cache,DisableParallel=true};
        restoreArgs.PreLoadedRequestProviders.Add(new DependencyGraphSpecRequestProvider(new RestoreCommandProvidersCache(),restoredGraph,reloaded));
        var results=await RestoreRunner.RunAsync(restoreArgs,CancellationToken.None);Require(results.Count==1&&results[0].Success,"actual offline NuGet73 restore");
        string assets=Path.Combine(project,"obj","project.assets.json");Require(File.Exists(assets),"committed assets file");
        var lockFile=new LockFileFormat().Read(assets);Require(lockFile.Libraries.Select(l=>l.Name).OrderBy(s=>s).SequenceEqual(new[]{"Owned.Dependency","Owned.Root"}),"resolved transitive dependency graph");
        Require(Directory.GetFiles(packages,"*.nupkg",SearchOption.AllDirectories).Length==2,"two packages extracted into owned cache");
        foreach(var metadata in Directory.GetFiles(packages,".nupkg.metadata",SearchOption.AllDirectories))
        {
            using var json=JsonDocument.Parse(File.ReadAllText(metadata));
            Require(json.RootElement.GetProperty("contentHash").GetString()!.Length>0,"source-generated nupkg metadata serialization");
        }
        Require(Directory.GetFiles(packages,".nupkg.metadata",SearchOption.AllDirectories).Length==2,"two source-generated metadata files");
        Console.WriteLine("PASS eight original NET10 NuGet libraries: upstream APIs="+api+",resource values="+strings+",schema/pack/archive,Unicode settings,DPAPI,local protocol,graph JSON,offline transitive restore and committed assets");
    }
}
