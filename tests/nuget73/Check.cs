using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.Versioning;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.Xml;
using System.Xml.Linq;
using Microsoft.CodeAnalysis;
using NuGet.Common;
using NuGet.Frameworks;
using NuGet.LibraryModel;
using NuGet.Versioning;

internal static class Check
{
    internal static void Require(bool ok,string message) { if(!ok)throw new Exception(message); }
    static async Task Main(string[] args)
    {
        string source=args[0],refs=args[1],baselines=args[2],work=args[3];
        var names=new[]{"NuGet.Versioning","NuGet.Frameworks","NuGet.Common","NuGet.LibraryModel"};
        var framework=Directory.GetFiles(refs,"*.dll").Select(p=>MetadataReference.CreateFromFile(p)).ToArray();
        Require(framework.Length==167,"NET10 references");
        int strings=0,api=0;
        foreach(var name in names)
        {
            var a=Assembly.Load(name);var n=a.GetName();
            Require(n.Version.ToString()=="7.3.0.0" && Convert.ToHexString(n.GetPublicKeyToken()).ToLowerInvariant()=="31bf3856ad364e35","identity "+name);
            Require(a.GetCustomAttribute<TargetFrameworkAttribute>().FrameworkName==".NETCoreApp,Version=v10.0","original framework "+name);
            Require(a.GetCustomAttribute<AssemblyFileVersionAttribute>().Version=="7.3.0.11413","original file version "+name);
            var path=Path.Combine(baselines,name+".txt");
            CheckApi.Run(framework,a.Location,path,names.Where(s=>s!=name).Select(s=>Path.Combine(AppContext.BaseDirectory,s+".dll")).ToArray());
            api+=File.ReadAllLines(path).Count(l=>!string.IsNullOrWhiteSpace(l)&&!l.StartsWith("#")&&!l.StartsWith("*REMOVED*"));
            foreach(var resx in Directory.GetFiles(Path.Combine(source,"src/NuGet.Core",name),"*.resx"))
            {
                string logical=name+"."+Path.GetFileNameWithoutExtension(resx)+".resources";
                using var set=new ResourceSet(a.GetManifestResourceStream(logical));
                using var reader=new XmlTextReader(resx);reader.WhitespaceHandling=WhitespaceHandling.All;
                foreach(var data in XDocument.Load(reader,LoadOptions.PreserveWhitespace).Root.Elements("data"))
                {
                    Require(set.GetString(data.Attribute("name").Value)==data.Element("value").Value,"resource "+logical+"/"+data.Attribute("name").Value);strings++;
                }
            }
        }
        var v=NuGetVersion.Parse("1.2.3-alpha.10+build.7");
        Require(v.ToNormalizedString()=="1.2.3-alpha.10","semver normalization");
        Require(VersionComparer.VersionRelease.Compare(v,NuGetVersion.Parse("1.2.3-alpha.2"))>0,"numeric prerelease ordering");
        Require(VersionComparer.VersionRelease.Equals(v,NuGetVersion.Parse("1.2.3-alpha.10+other")),"build metadata equality");
        var range=VersionRange.Parse("[1.0.0,2.0.0)");Require(range.Satisfies(NuGetVersion.Parse("1.9.9"))&&!range.Satisfies(NuGetVersion.Parse("2.0.0")),"range bounds");
        var vectors=JsonSerializer.Deserialize<string[][]>(File.ReadAllText(Path.Combine(baselines,"upstream-range-vectors.json")));
        foreach(var vector in vectors)
        {
            var parsed=VersionRange.Parse(vector[0]);var formatter=new VersionRangeFormatter();
            Require(parsed.PrettyPrint()==vector[1] && parsed.ToString("P",formatter)==vector[1] && string.Format(formatter,"{0:P}",parsed)==vector[1],"original range vector "+vector[0]);
        }
        var target=NuGetFramework.ParseFolder("net10.0");Require(target.Version.Major==10&&target.GetShortFolderName()=="net10.0","NET10 framework");
        var reducer=new FrameworkReducer();var nearest=reducer.GetNearest(target,new[]{NuGetFramework.ParseFolder("netstandard2.0"),NuGetFramework.ParseFolder("net8.0"),NuGetFramework.ParseFolder("net9.0")});
        Require(nearest.GetShortFolderName()=="net9.0","nearest compatible framework");
        Require(!DefaultCompatibilityProvider.Instance.IsCompatible(NuGetFramework.ParseFolder("net8.0"),target),"future framework incompatible");
        Require(NuGetFramework.ParseFolder("net10.0-windows10.0.19041.0").Platform=="windows","platform framework");
        var libraryRange=new LibraryRange("Grüße 世界",range,LibraryDependencyTarget.Package);var dependency=new LibraryDependency(libraryRange){NoWarn=default,Aliases="global",VersionCentrallyManaged=true};var copy=new LibraryDependency(dependency);
        Require(copy.Equals(dependency)&&copy.Name=="Grüße 世界"&&copy.NoWarn==ImmutableArray<NuGetLogCode>.Empty&&copy.VersionCentrallyManaged,"library model copy/required properties/default immutable");
        Directory.CreateDirectory(work);Environment.SetEnvironmentVariable("NUGET_SCRATCH",Path.Combine(work,"scratch"));
        string file=Path.Combine(work,"counter 世界.txt");File.WriteAllText(file,"0");
        await Task.WhenAll(Enumerable.Range(0,24).Select(_=>ConcurrencyUtilities.ExecuteWithFileLockedAsync(file,async ct=> {int value=int.Parse(File.ReadAllText(file),CultureInfo.InvariantCulture);await Task.Yield();File.WriteAllText(file,(value+1).ToString(CultureInfo.InvariantCulture));return true;},CancellationToken.None)));
        Require(File.ReadAllText(file)=="24","concurrent native file locking");
        Require(PathUtility.EnsureTrailingForwardSlash("Grüße 世界")=="Grüße 世界/","Unicode path utility");
        Console.WriteLine("PASS original NET10 NuGet foundation APIs="+api+",neutral strings="+strings+",upstream range vectors="+vectors.Length+",SemVer/TFM/library models/24 concurrent file locks");
    }
}
