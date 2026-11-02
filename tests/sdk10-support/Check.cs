using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Hashing;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Text;
using System.Text.Json;
using System.Xml;
using System.Xml.Linq;
using Microsoft.Extensions.DependencyModel;
using Microsoft.NET.HostModel.AppHost;
using Microsoft.NET.HostModel.Bundle;
internal static class Check
{
    static void Require(bool ok,string message){if(!ok)throw new Exception(message);}
    static byte[] Hash(string name,byte[] bytes)=>name switch {"Crc32"=>Crc32.Hash(bytes),"Crc64"=>Crc64.Hash(bytes),"XxHash32"=>XxHash32.Hash(bytes),"XxHash64"=>XxHash64.Hash(bytes),"XxHash3"=>XxHash3.Hash(bytes),"XxHash128"=>XxHash128.Hash(bytes),_=>throw new Exception(name)};
    static void Main(string[] args)
    {
        using var vectors=JsonDocument.Parse(File.ReadAllText(args[0]));int count=0;
        foreach(var vector in vectors.RootElement.EnumerateArray())
        {
            string algorithm=vector.GetProperty("algorithm").GetString()!;byte[] bytes=Convert.FromHexString(vector.GetProperty("input").GetString()!);string expected=vector.GetProperty("expected").GetString()!;
            Require(Convert.ToHexString(Hash(algorithm,bytes))==expected,"original vector "+algorithm+"/"+vector.GetProperty("name").GetString());
            var type=typeof(Crc32).Assembly.GetType("System.IO.Hashing."+algorithm)!;
            var instance=(NonCryptographicHashAlgorithm)Activator.CreateInstance(type)!;
            for(int start=0;start<bytes.Length;start+=3)instance.Append(bytes.AsSpan(start,Math.Min(3,bytes.Length-start)));
            Require(Convert.ToHexString(instance.GetCurrentHash())==expected,"original streaming vector "+algorithm);Require(Convert.ToHexString(instance.GetHashAndReset())==expected,"original reset vector "+algorithm);count++;
        }
        foreach(var algorithm in new[]{"Crc32","Crc64","XxHash32","XxHash64","XxHash3","XxHash128"})
        {
            byte[] bytes=Enumerable.Range(0,65539).Select(i=>(byte)(i*17+13)).ToArray();var expected=Hash(algorithm,bytes);
            var instance=(NonCryptographicHashAlgorithm)Activator.CreateInstance(typeof(Crc32).Assembly.GetType("System.IO.Hashing."+algorithm)!)!;
            for(int start=0;start<bytes.Length;start+=257)instance.Append(bytes.AsSpan(start,Math.Min(257,bytes.Length-start)));
            Require(instance.GetCurrentHash().SequenceEqual(expected),"large incremental "+algorithm);Span<byte> shortBuffer=stackalloc byte[1];Require(!instance.TryGetCurrentHash(shortBuffer,out int written)&&written==0,"short output buffer "+algorithm);
        }
        int resourceCount=0;
        foreach(var pair in new[]{(typeof(Crc32).Assembly,"System.IO.Hashing"),(typeof(DependencyContext).Assembly,"Microsoft.Extensions.DependencyModel"),(typeof(HostWriter).Assembly,"Microsoft.NET.HostModel")})
        {
            var a=pair.Item1;Require(a.GetName().Version!.ToString()==(pair.Item2=="Microsoft.NET.HostModel"?"10.0.2.0":"10.0.0.0"),"original assembly version");
            Require(a.GetCustomAttribute<AssemblyFileVersionAttribute>()!.Version=="10.0.225.61305","Arcade file version");Require(a.GetCustomAttribute<TargetFrameworkAttribute>()!.FrameworkName==".NETCoreApp,Version=v10.0","original NET10 profile");
            string token=Convert.ToHexString(a.GetName().GetPublicKeyToken()!).ToLowerInvariant();Require(token==(pair.Item2=="System.IO.Hashing"?"cc7b13ffcd2ddd51":"adb9793829ddae60"),"original key policy");
            if(pair.Item2=="Microsoft.NET.HostModel")continue;
            string logical="FxResources."+pair.Item2+".SR";using var set=new ResourceSet(a.GetManifestResourceStream(logical+".resources")!);
            string path=Path.Combine(args[1],"src","libraries",pair.Item2,"src","Resources","Strings.resx");using var reader=new XmlTextReader(path);reader.WhitespaceHandling=WhitespaceHandling.All;
            foreach(var data in XDocument.Load(reader,LoadOptions.PreserveWhitespace).Root!.Elements("data")){Require(set.GetString(data.Attribute("name")!.Value)==data.Element("value")!.Value,"original resource");resourceCount++;}
        }
        if(args.Length>4&&args[4]=="--hash-only"){Console.WriteLine("PASS fallback hashing original vectors="+count+",resource values="+resourceCount);return;}
        string json="""
        {"runtimeTarget":{"name":".NETCoreApp,Version=v10.0","signature":"Grüsse 世界"},"compilationOptions":{"defines":["UNICODE_世界"],"languageVersion":"preview"},"targets":{".NETCoreApp,Version=v10.0":{"Owned.Library/1.2.3":{"runtime":{"lib/net10.0/Owned.Library.dll":{"assemblyVersion":"1.2.3.0","fileVersion":"1.2.3.4"}},"compile":{"ref/net10.0/Owned.Library.dll":{}},"resources":{"fr/Owned.resources.dll":{"locale":"fr"}}}}},"libraries":{"Owned.Library/1.2.3":{"type":"project","serviceable":false,"sha512":""}},"runtimes":{"win-x64":["win","any"]}}
        """;
        using var input=new MemoryStream(Encoding.UTF8.GetBytes(json));using var depsReader=new DependencyContextJsonReader();var deps=depsReader.Read(input);
        Require(deps.RuntimeLibraries.Single().Name=="Owned.Library"&&deps.CompileLibraries.Single().Assemblies.Single()=="ref/net10.0/Owned.Library.dll","deps original assets");
        Require(deps.RuntimeLibraries.Single().RuntimeAssemblyGroups.Single().RuntimeFiles.Single().AssemblyVersion=="1.2.3.0","deps assembly metadata");
        using var output=new MemoryStream();new DependencyContextWriter().Write(deps,output);output.Position=0;var roundtrip=depsReader.Read(output);
        Require(roundtrip.Target.RuntimeSignature=="Grüsse 世界"&&roundtrip.RuntimeGraph.Single().Fallbacks.SequenceEqual(new[]{"win","any"}),"deps Unicode/runtime-graph roundtrip");
        string work=args[2],template=args[3];Directory.CreateDirectory(work);string app=Path.Combine(work,"owned 世界.exe");HostWriter.CreateAppHost(template,app,"Hello.dll");
        string child=Run(app,new[]{"Grüsse 世界","quoted \"value\"",""});Require(child.Contains("SOURCE NET10 hello:10.0.5|Grüsse 世界|quoted \"value\"|"),"created native apphost execution");
        bool tooLong=false;try{HostWriter.CreateAppHost(template,Path.Combine(work,"too-long.exe"),new string('x',2048));}catch(AppNameTooLongException){tooLong=true;}Require(tooLong,"oversized apphost path rejection");
        var bundler=new Bundler(Path.GetFileName(app),Path.Combine(work,"bundle"),targetOS:OSPlatform.Windows,targetArch:Architecture.X64,targetFrameworkVersion:new Version(10,0),appAssemblyName:"Hello");
        string bundle=bundler.GenerateBundle(new[]{new FileSpec(app,Path.GetFileName(app)),new FileSpec(Path.Combine(work,"Hello.dll"),"Hello.dll"),new FileSpec(Path.Combine(work,"Hello.runtimeconfig.json"),"Hello.runtimeconfig.json")});
        Require(Bundler.IsBundle(bundle,out long offset)&&offset>0,"original bundle header generation");
        string bundled=Run(bundle,new[]{"Grüsse 世界","quoted \"value\"",""});Require(bundled.Contains("SOURCE NET10 hello:10.0.5|Grüsse 世界|quoted \"value\"|"),"generated native bundle execution");
        Console.WriteLine("PASS exact SDK10 support: original hash vectors="+count+",resource values="+resourceCount+",deps Unicode/metadata/runtime graph roundtrip,native Unicode apphost and bundle execution");
    }
    static string Run(string path,string[] args){var p=new ProcessStartInfo(path){UseShellExecute=false,RedirectStandardOutput=true,RedirectStandardError=true};foreach(var arg in args)p.ArgumentList.Add(arg);using var child=Process.Start(p)!;string text=child.StandardOutput.ReadToEnd(),error=child.StandardError.ReadToEnd();Require(child.WaitForExit(45000),"owned native child timeout");Require(child.ExitCode==0,"owned native child exit "+child.ExitCode+" "+error);return text;}
}
