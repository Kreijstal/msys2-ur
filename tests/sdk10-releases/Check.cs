using System;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.Loader;
using System.Runtime.Versioning;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Xml;
using System.Xml.Linq;
using Microsoft.Deployment.DotNet.Releases;
using Xunit;
internal static class Check
{
    static void Require(bool ok,string text){if(!ok)throw new Exception(text);}
    static async Task Main(string[] args)
    {
        CultureInfo.CurrentUICulture=CultureInfo.GetCultureInfo("en-US");
        var library=typeof(ProductCollection).Assembly;Require(library.GetName().Version!.ToString()=="2.0.0.0"&&Convert.ToHexString(library.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="31bf3856ad364e35","original Releases identity");
        Require(library.GetCustomAttribute<TargetFrameworkAttribute>()!.FrameworkName==".NETStandard,Version=v2.0","original Standard2 target");Require(library.GetCustomAttribute<AssemblyFileVersionAttribute>()!.Version=="2.0.25.61305","original Arcade file version");
        Require(library.GetReferencedAssemblies().Single(a=>a.Name=="System.Text.Json").Version!.ToString()=="8.0.0.0","original JSON8 assembly reference");
        int rejected=0;using(var refs=JsonDocument.Parse(File.ReadAllText(args[0])))foreach(var item in refs.RootElement.GetProperty("projects").EnumerateArray())
        {
            string path=item.GetProperty("output").GetString()!;var context=new AssemblyLoadContext("reference-only "+rejected,true);bool blocked=false;
            try{context.LoadFromAssemblyPath(path);}catch(BadImageFormatException){blocked=true;}finally{context.Unload();}
            Require(blocked,"reference assembly was loadable as runtime implementation: "+path);rejected++;
        }
        Require(rejected==9,"all nine original references runtime-rejected");
        var fixture=new Microsoft.Deployment.DotNet.Releases.Tests.ReleaseVersionTests();int methods=0,cases=0;
        foreach(var method in fixture.GetType().GetMethods(BindingFlags.Public|BindingFlags.Instance|BindingFlags.DeclaredOnly))
        {
            if(method.GetCustomAttribute<FactAttribute>() is not null){method.Invoke(fixture,null);methods++;cases++;}
            else if(method.GetCustomAttribute<TheoryAttribute>() is not null){foreach(var row in method.GetCustomAttributes<InlineDataAttribute>()){method.Invoke(fixture,row.Data);cases++;}methods++;}
        }
        Require(methods==29,"all unchanged upstream version-test methods");
        string source=args[1],work=args[2];Directory.CreateDirectory(work);string upstream=Path.Combine(source,"src/deployment-tools/src/Microsoft.Deployment.DotNet.Releases");string data=Path.Combine(upstream,"tests/data");
        string index=Path.Combine(work,"releases-index 世界.json");File.WriteAllText(index,File.ReadAllText(Path.Combine(data,"releases-index.json")).Replace("\"product\": \".NET\"","\"product\": \".NET 世界\""),Encoding.UTF8);
        var products=await ProductCollection.GetFromFileAsync(index,false);Require(products.Count>0&&products.Any(p=>p.ProductName==".NET 世界"),"owned Unicode index parse");int releases=0,files=0,cves=0,channels=0;
        foreach(var product in products)
        {
            string input=Path.Combine(data,product.ProductVersion,"releases.json");if(!File.Exists(input))continue;
            var list=await product.GetReleasesAsync(input,false);var unbound=await Product.GetReleasesAsync(input);Require(list.Count==unbound.Count,"instance/static release parse");
            foreach(var release in list){Require(ReferenceEquals(release.Product,product),"release parent binding");Require(release.Version.Major>=0,"parsed release version");releases++;files+=release.Files.Count;cves+=release.Cves.Count;}
            channels++;
        }
        Require(channels>1&&releases>1&&files>0,"original release fixture coverage");
        string resx=Path.Combine(upstream,"src/ReleasesResources.resx");using var set=new ResourceSet(library.GetManifestResourceStream("Microsoft.Deployment.DotNet.Releases.ReleasesResources.resources")!);using var reader=new XmlTextReader(resx);reader.WhitespaceHandling=WhitespaceHandling.All;int values=0;
        foreach(var item in XDocument.Load(reader,LoadOptions.PreserveWhitespace).Root!.Elements("data")){Require(set.GetString(item.Attribute("name")!.Value)==item.Element("value")!.Value,"original neutral resource");values++;}
        var jsonAssembly=typeof(JsonDocument).Assembly;Require(Path.GetFullPath(jsonAssembly.Location).StartsWith(Path.GetFullPath(args[3]),StringComparison.OrdinalIgnoreCase),"real JSON implementation from source runtime");Require(!jsonAssembly.GetCustomAttributes().Any(a=>a.GetType().Name=="ReferenceAssemblyAttribute"),"runtime JSON is executable implementation");
        Console.WriteLine("PASS Releases original NS2 on "+Environment.Version+": upstream version methods="+methods+",cases="+cases+",channels="+channels+",releases="+releases+",files="+files+",CVEs="+cves+",neutral strings="+values+",reference assemblies rejected="+rejected+",Unicode/local fixture parsing;real JSON="+jsonAssembly.GetName().Version);
    }
}
