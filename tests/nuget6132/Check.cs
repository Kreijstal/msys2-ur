using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.Loader;
using System.Resources;
using System.Security.Cryptography;
using System.Security.Cryptography.Pkcs;
using System.Security.Cryptography.X509Certificates;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using NuGet.Common;
using NuGet.Configuration;
using NuGet.Credentials;
using NuGet.Frameworks;
using NuGet.Packaging;
using NuGet.Packaging.Core;
using NuGet.Protocol;
using NuGet.Protocol.Core.Types;
using NuGet.Versioning;

internal static class Check
{
    internal static void Require(bool ok,string message) {if(!ok)throw new Exception(message);}
    static async Task Main(string[] args)
    {
        RunApi(args);
        var context = new AssemblyLoadContext("exact-source-NuGet6132-runtime", isCollectible:true);
        context.Resolving += (owner, name) => {
            string file=Path.Combine(AppContext.BaseDirectory,name.Name+".dll");
            return File.Exists(file) ? owner.LoadFromAssemblyPath(file) : null;
        };
        foreach(string name in new[]{"System.Collections.Immutable","System.Security.Cryptography.ProtectedData","System.Security.Cryptography.Pkcs","System.Formats.Asn1"})
            context.LoadFromAssemblyPath(Path.Combine(AppContext.BaseDirectory,name+".dll"));
        var assembly=context.LoadFromAssemblyPath(typeof(Check).Assembly.Location);
        var task=(Task)assembly.GetType("Check")!.GetMethod("RunRuntime",BindingFlags.Static|BindingFlags.NonPublic)!.Invoke(null,new object[]{args})!;
        await task;
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static void RunApi(string[] args)
    {
        string source=args[0],refs=args[1],baselines=args[2],work=args[3];
        string[] names={"NuGet.Versioning","NuGet.Frameworks","NuGet.Common","NuGet.Configuration","NuGet.Packaging","NuGet.Protocol","NuGet.Credentials"};
        var framework=Directory.GetFiles(refs,"*.dll").Select(p=>MetadataReference.CreateFromFile(p));
        foreach(var name in names)
        {
            var assembly=Assembly.Load(name);Require(assembly.GetName().Version!.ToString()=="6.13.2.1",name+" original identity");
            Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="31bf3856ad364e35",name+" public key");
            Require(assembly.GetCustomAttribute<System.Runtime.Versioning.TargetFrameworkAttribute>()!.FrameworkName==".NETCoreApp,Version=v10.0",name+" original NET10 source-only profile");
            CheckApi.Run(framework,assembly.Location,Path.Combine(baselines,name+".txt"),names.Where(n=>n!=name).Select(n=>Path.Combine(AppContext.BaseDirectory,n+".dll")).Concat(new[]{"Newtonsoft.Json","System.Security.Cryptography.Pkcs","System.Security.Cryptography.ProtectedData"}.Select(n=>Path.Combine(AppContext.BaseDirectory,n+".dll"))).ToArray());
        }
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static async Task RunRuntime(string[] args)
    {
        string work=args[3];
        var context=AssemblyLoadContext.GetLoadContext(typeof(Check).Assembly)!;
        foreach(var item in new[]{("System.Collections.Immutable","8.0.0.0"),("System.Security.Cryptography.ProtectedData","4.0.2.0"),("System.Security.Cryptography.Pkcs","6.0.0.0"),("System.Formats.Asn1","8.0.0.0")})
        {
            var dependency=context.LoadFromAssemblyName(new AssemblyName(item.Item1));
            Require(dependency.GetName().Version!.ToString()==item.Item2,item.Item1+" exact source assembly version");
            Require(dependency.Location==Path.Combine(AppContext.BaseDirectory,item.Item1+".dll"),item.Item1+" exact restored source implementation");
        }
        foreach(var item in new[]{("NuGet.Common","System.Collections.Immutable","8.0.0.0"),("NuGet.Configuration","System.Security.Cryptography.ProtectedData","4.0.2.0"),("NuGet.Packaging","System.Security.Cryptography.Pkcs","6.0.0.0")})
        {
            var assembly=context.LoadFromAssemblyName(new AssemblyName(item.Item1));
            Require(assembly.GetReferencedAssemblies().Single(a=>a.Name==item.Item2).Version!.ToString()==item.Item3,item.Item1+" compiled against exact dependency");
            Require(assembly.Location==Path.Combine(AppContext.BaseDirectory,item.Item1+".dll"),item.Item1+" exact source implementation");
        }
        Require(NuGetVersion.Parse("1.2.3-preview.4+build").ToNormalizedString()=="1.2.3-preview.4","SemVer normalization");
        Require(VersionRange.Parse("[1.0.0,2.0.0)").Satisfies(NuGetVersion.Parse("1.5.0")),"version range");
        var tfm=NuGetFramework.ParseFolder("net10.0");Require(tfm.GetShortFolderName()=="net10.0","framework parsing");
        Directory.CreateDirectory(work);string feed=Path.Combine(work,"feed 世界");Directory.CreateDirectory(feed);
        File.WriteAllText(Path.Combine(work,"NuGet.Config"),"<configuration><packageSources><clear/></packageSources></configuration>");
        var settings=Settings.LoadSpecificSettings(work,"NuGet.Config");settings.AddOrUpdate("packageSources",new SourceItem("owned",feed));settings.SaveToDisk();
        Require(new PackageSourceProvider(Settings.LoadSpecificSettings(work,"NuGet.Config")).LoadPackageSources().Select(p=>Path.GetFullPath(p.Source)).Single()==Path.GetFullPath(feed),"owned config roundtrip");
        string secret="synthetic 世界 "+Guid.NewGuid();string encrypted=EncryptionUtility.EncryptString(secret);Require(encrypted!=secret && EncryptionUtility.DecryptString(encrypted)==secret,"current-user DPAPI");
        string marker=Path.Combine(work,"_._");File.WriteAllText(marker,"");
        foreach(string id in new[]{"Owned.Dependency","Owned.Root"})
        {
            var builder=new PackageBuilder {Id=id,Version=NuGetVersion.Parse("1.0.0"),Description="Owned offline NuGet6.13.2 fixture"};builder.Authors.Add("source-test");builder.Files.Add(new PhysicalPackageFile {SourcePath=marker,TargetPath="lib/net10.0/_._"});
            if(id=="Owned.Root")builder.DependencyGroups.Add(new PackageDependencyGroup(tfm,new[]{new PackageDependency("Owned.Dependency",VersionRange.Parse("[1.0.0]"))}));
            string path=Path.Combine(feed,id+".1.0.0.nupkg");using(var output=File.Create(path))builder.Save(output);
            using var reader=new PackageArchiveReader(path);Require(reader.GetIdentity().Id==id && reader.GetFiles().Contains("lib/net10.0/_._"),"package/schema/archive "+id);
        }
        using var cache=new SourceCacheContext();var repository=Repository.Factory.GetCoreV3(feed);var lookup=await repository.GetResourceAsync<FindPackageByIdResource>();
        Require((await lookup.GetAllVersionsAsync("Owned.Root",cache,NullLogger.Instance,CancellationToken.None)).Single().ToNormalizedString()=="1.0.0","local package enumeration");
        using var copied=new MemoryStream();Require(await lookup.CopyNupkgToStreamAsync("Owned.Root",NuGetVersion.Parse("1.0.0"),copied,cache,NullLogger.Instance,CancellationToken.None),"local package download");
        Require(copied.ToArray().SequenceEqual(File.ReadAllBytes(Path.Combine(feed,"Owned.Root.1.0.0.nupkg"))),"downloaded package bytes");
        var dependencies=await repository.GetResourceAsync<DependencyInfoResource>();var root=await dependencies.ResolvePackage(new PackageIdentity("Owned.Root",NuGetVersion.Parse("1.0.0")),tfm,cache,NullLogger.Instance,CancellationToken.None);
        Require(root.Dependencies.Single().Id=="Owned.Dependency","protocol dependency graph");
        var provider=new OwnedCredentials();var service=new CredentialService(new AsyncLazy<IEnumerable<ICredentialProvider>>(()=>Task.FromResult<IEnumerable<ICredentialProvider>>(new[]{provider})),nonInteractive:true,handlesDefaultCredentials:false);
        var uri=new Uri("https://owned.invalid/feed");var credentials=await service.GetCredentialsAsync(uri,null,CredentialRequestType.Unauthorized,"owned fixture",CancellationToken.None);
        Require(credentials!.GetCredential(uri,"Basic")!.UserName=="owned" && provider.Calls==1,"noninteractive credential provider");
        using var rsa=RSA.Create(2048);var request=new CertificateRequest("CN=Owned NuGet source check",rsa,System.Security.Cryptography.HashAlgorithmName.SHA256,RSASignaturePadding.Pkcs1);using var cert=request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-1),DateTimeOffset.UtcNow.AddMinutes(5));
        var cms=new SignedCms(new ContentInfo(new byte[]{1,2,3,4}));cms.ComputeSignature(new CmsSigner(cert));cms.CheckSignature(true);
        Console.WriteLine("PASS seven original NuGet6.13.2 NET10 identities/APIs; exact Immutable8/ProtectedData4/Pkcs6 compiled bindings and isolated source implementations including Asn1 8; SemVer/frameworks; owned config/DPAPI; package/schema/archive; local protocol lookup/download/dependencies; noninteractive synthetic credentials; ephemeral PKCS signing");
    }
    sealed class OwnedCredentials : ICredentialProvider
    {
        public int Calls;public string Id=>"owned-fixture";
        public Task<CredentialResponse> GetAsync(Uri uri,IWebProxy proxy,CredentialRequestType type,string message,bool isRetry,bool nonInteractive,CancellationToken cancellationToken)
        {Require(nonInteractive,"no credential prompt");Calls++;return Task.FromResult(new CredentialResponse(new NetworkCredential("owned","synthetic")));}
    }
}
