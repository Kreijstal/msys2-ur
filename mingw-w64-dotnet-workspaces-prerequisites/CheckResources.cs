using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Security.Cryptography;
using System.Text.Json;

internal static class CheckResources
{
    internal static void Run(string resourceManifest,string librariesManifest)
    {
        using var libraries=JsonDocument.Parse(File.ReadAllText(librariesManifest));
        foreach(var library in libraries.RootElement.EnumerateArray())
        {
            string name=library.GetProperty("id").GetString();
            var assembly=Assembly.Load(new AssemblyName(name));
            string token=library.GetProperty("key").GetString() switch {
                "Open"=>"cc7b13ffcd2ddd51","Microsoft"=>"b03f5f7f11d50a3a","ECMA"=>"b77a5c561934e089","MicrosoftShared"=>"31bf3856ad364e35",_=>throw new Exception("unexpected key")};
            if(assembly.GetName().Version!=new Version(8,0,0,0)||Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()!=token)throw new Exception("identity: "+name);
            if(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>().Version!="8.0.31.0" ||
                assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion!=library.GetProperty("version").GetString()+"+runtime-v8.0.31")throw new Exception("source version: "+name);
            string relative=Path.GetRelativePath(AppContext.BaseDirectory,assembly.Location).Replace(Path.DirectorySeparatorChar,'/');
            if(relative!=name+".dll" && relative!="runtimes/win/lib/net8.0/"+name+".dll")throw new Exception("implementation location: "+assembly.Location);
            assembly.GetExportedTypes();
            if(assembly.GetCustomAttribute<CLSCompliantAttribute>()?.IsCompliant!=true)throw new Exception("CLS compliance: "+name);
        }
        using var manifest=JsonDocument.Parse(File.ReadAllText(resourceManifest));
        int sets=0,strings=0;
        foreach(var entry in manifest.RootElement.EnumerateArray())
        {
            var assembly=Assembly.Load(new AssemblyName(entry.GetProperty("assembly").GetString()));
            string name=entry.GetProperty("resource").GetString()+".resources";
            using var reader=new ResourceReader(assembly.GetManifestResourceStream(name)??throw new Exception(name));
            var actual=reader.Cast<DictionaryEntry>().ToDictionary(e=>(string)e.Key,e=>(string)e.Value);
            foreach(var pair in entry.GetProperty("strings").EnumerateObject())
            {
                if(!actual.TryGetValue(pair.Name,out var value)||value!=pair.Value.GetString())throw new Exception("resource string: "+name+"/"+pair.Name);
                strings++;
            }
            if(actual.Count!=entry.GetProperty("strings").EnumerateObject().Count())throw new Exception("resource count: "+name);
            sets++;
        }
        if(sets!=5)throw new Exception("five upstream resource sets expected");
        foreach(System.Diagnostics.ProcessModule module in System.Diagnostics.Process.GetCurrentProcess().Modules)
            if(module.FileName.Contains("\\Microsoft.NET\\Framework",StringComparison.OrdinalIgnoreCase))throw new Exception("Framework implementation loaded: "+module.FileName);
        Console.WriteLine($"PASS six source assembly identities/versions/locations; all exported types; {sets} resource sets/{strings} strings; no Framework implementations");
    }
}
