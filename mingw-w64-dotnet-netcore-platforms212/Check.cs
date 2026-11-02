using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;
using NuGet.RuntimeModel;
class Program
{
    static void Main()
    {
        string path=Path.Combine(AppContext.BaseDirectory,"source-runtime.json");
        if(Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant()!="e5c6c05c5f65ba037d080e35cf04ee29e2796e55281cd71b4e7911a74e9b9824")throw new Exception("Source graph bytes differ");
        using var doc=JsonDocument.Parse(File.ReadAllText(path));
        var values=doc.RootElement.GetProperty("runtimes").EnumerateObject().ToDictionary(p=>p.Name,p=>p.Value.TryGetProperty("#import",out var x)?x.EnumerateArray().Select(a=>a.GetString()).ToArray():Array.Empty<string>());
        if(values.Count!=515)throw new Exception("RID count");
        var graph=JsonRuntimeFormat.ReadRuntimeGraph(path);
        foreach(string rid in values.Keys)
        {
            var seen=new HashSet<string>();var visiting=new HashSet<string>();
            void Visit(string item)
            {
                if(visiting.Contains(item))throw new Exception("RID cycle "+item);
                if(!values.ContainsKey(item))throw new Exception("Missing imported RID "+item);
                if(!seen.Add(item))return;
                visiting.Add(item);foreach(string parent in values[item])Visit(parent);visiting.Remove(item);
            }
            Visit(rid);
            if(!seen.SetEquals(graph.ExpandRuntime(rid)))throw new Exception("NuGet runtime expansion "+rid);
        }
        var windows=graph.ExpandRuntime("win10-x64").ToArray();
        foreach(string rid in new[]{"win10-x64","win81-x64","win8-x64","win7-x64","win-x64","win","any","base"})
            if(!windows.Contains(rid))throw new Exception("Windows fallback "+rid);
        foreach(var pair in new[]{("ubuntu.16.04-x64","linux-x64"),("linuxmint.18-x64","ubuntu.16.04-x64"),("osx.10.12-x64","osx-x64"),("rhel.7.2-x64","rhel.7-x64")})
            if(!graph.ExpandRuntime(pair.Item1).Contains(pair.Item2))throw new Exception("OS fallback "+pair);
        Console.WriteLine("PASS exact source runtime graph hash, 515 RIDs, import closure/cycle checks and NuGet fallback expansion for every RID");
        Console.WriteLine("PASS Windows 10/8.1/8/7, Ubuntu/Mint, RHEL and macOS fallback chains");
        Console.WriteLine("NuGet model: "+typeof(RuntimeGraph).Assembly.Location);
    }
}
