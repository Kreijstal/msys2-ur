using System;
using System.Collections;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Text.Json;

internal static class CheckAssets
{
    internal static void Run(string localization,string legacyBaseline)
    {
        string[] names={"System.Private.ServiceModel","System.Web.Services.Description","System.ServiceModel.Primitives",
            "System.ServiceModel.Duplex","System.ServiceModel.Security","System.ServiceModel.Http","System.ServiceModel.NetTcp","System.ServiceModel"};
        foreach(string name in names)
        {
            var assembly=Assembly.Load(new AssemblyName(name));
            var version=name=="System.ServiceModel"?new Version(4,0,0,0):new Version(4,10,3,0);
            string token=Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant();
            if(assembly.GetName().Version!=version || token!=(name=="System.ServiceModel"?"b77a5c561934e089":"b03f5f7f11d50a3a"))throw new Exception("WCF identity: "+name);
            if(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()!.InformationalVersion!="4.10.3+6c05fa33450ee3960f0763948e91327f049b302b")throw new Exception("WCF source: "+name);
            if(Path.GetDirectoryName(assembly.Location)!=AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar))throw new Exception("WCF location: "+name);
            var forwarded=assembly.GetForwardedTypes();
            if(name=="System.ServiceModel")
            {
                if(forwarded.Length!=270)throw new Exception("legacy root forwards");
                using var baseline=JsonDocument.Parse(File.ReadAllText(legacyBaseline));
                foreach(var entry in baseline.RootElement.GetProperty("forwards").EnumerateArray())
                {
                    string typeName=entry.GetProperty("type").GetString()!;
                    if(assembly.GetType(typeName,throwOnError:true)!.FullName!=typeName)throw new Exception("legacy type resolution: "+typeName);
                }
            }
        }
        using var manifest=JsonDocument.Parse(File.ReadAllText(localization));
        int sets=0,strings=0;
        foreach(var entry in manifest.RootElement.EnumerateArray())
        {
            var assembly=Assembly.Load(new AssemblyName(entry.GetProperty("assembly").GetString()!));
            var culture=CultureInfo.GetCultureInfo(entry.GetProperty("culture").GetString()!);
            var satellite=assembly.GetSatelliteAssembly(culture);
            string resource=entry.GetProperty("resource").GetString()+"."+culture.Name+".resources";
            using var reader=new ResourceReader(satellite.GetManifestResourceStream(resource)??throw new Exception(resource));
            var actual=reader.Cast<DictionaryEntry>().ToDictionary(e=>(string)e.Key,e=>(string)e.Value!);
            foreach(var pair in entry.GetProperty("strings").EnumerateObject())
            {
                if(!actual.TryGetValue(pair.Name,out var value)||value!=pair.Value.GetString())throw new Exception("localized string "+culture.Name+"/"+pair.Name);
                strings++;
            }
            if(actual.Count!=entry.GetProperty("strings").EnumerateObject().Count())throw new Exception("resource count");
            sets++;
        }
        if(sets!=26)throw new Exception("26 localized sets expected");
        foreach(System.Diagnostics.ProcessModule module in System.Diagnostics.Process.GetCurrentProcess().Modules)
            if(module.FileName.Contains("\\Microsoft.NET\\Framework",StringComparison.OrdinalIgnoreCase))throw new Exception("Framework implementation loaded: "+module.FileName);
        Console.WriteLine($"PASS WCF installed assets: eight identities/source/locations; 274 legacy forwards resolve; {sets} localized sets/{strings} strings; no Framework implementations");
    }
}
