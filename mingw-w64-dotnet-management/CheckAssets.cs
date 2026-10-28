using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Text.Json;
using System.Management;

internal static class CheckAssets
{
    internal static void Run(string manifest)
    {
        var assembly=typeof(ManagementObject).Assembly;
        if(assembly.GetName().Version!=new Version(8,0,0,0)||Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()!="b03f5f7f11d50a3a")throw new Exception("WMI identity");
        if(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>().Version!="8.0.31.0" ||
           assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion!="8.0.0+runtime-v8.0.31")throw new Exception("WMI source version");
        string path=Path.GetRelativePath(AppContext.BaseDirectory,assembly.Location).Replace(Path.DirectorySeparatorChar,'/');
        if(path!="System.Management.dll" && path!="runtimes/win/lib/net8.0/System.Management.dll")throw new Exception("WMI implementation location");
        assembly.GetExportedTypes();
        using var data=JsonDocument.Parse(File.ReadAllText(manifest));
        if(data.RootElement.GetArrayLength()!=1)throw new Exception("resource manifest");
        var entry=data.RootElement[0];
        using var reader=new ResourceReader(assembly.GetManifestResourceStream(entry.GetProperty("resource").GetString()+".resources"));
        var actual=reader.Cast<DictionaryEntry>().ToDictionary(e=>(string)e.Key,e=>(string)e.Value);
        foreach(var pair in entry.GetProperty("strings").EnumerateObject())
            if(!actual.TryGetValue(pair.Name,out var value)||value!=pair.Value.GetString())throw new Exception("resource "+pair.Name);
        if(actual.Count!=entry.GetProperty("strings").EnumerateObject().Count())throw new Exception("resource count");
        Console.WriteLine("PASS WMI identity/source/location, exported types and "+actual.Count+" resource strings");
    }
}
