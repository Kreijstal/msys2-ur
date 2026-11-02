using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using NuGet.RuntimeModel;

static class Program
{
    static void Main(string[] args)
    {
        using var data = JsonDocument.Parse(File.ReadAllText(args[0]));
        var graph = JsonRuntimeFormat.ReadRuntimeGraph(args[0]);
        if (graph.Runtimes.Count != 22 || graph.Supports.Count != 14) throw new Exception("Graph row counts");
        int edges = 0;
        foreach (var rid in data.RootElement.GetProperty("runtimes").EnumerateObject())
        {
            var actual = graph.Runtimes[rid.Name];
            if (actual.RuntimeDependencySets.Count != rid.Value.EnumerateObject().Count()) throw new Exception("Owner count");
            foreach (var owner in rid.Value.EnumerateObject())
            {
                var set = actual.RuntimeDependencySets[owner.Name];
                if (set.Dependencies.Count != owner.Value.EnumerateObject().Count()) throw new Exception("Dependency count");
                foreach (var entry in owner.Value.EnumerateObject())
                {
                    var dep = set.Dependencies[entry.Name];
                    if (dep.Id != entry.Name || dep.VersionRange.MinVersion!.ToNormalizedString() != entry.Value.GetString() ||
                        !dep.VersionRange.IsMinInclusive || dep.VersionRange.MaxVersion != null) throw new Exception("Original version range");
                    edges++;
                }
                var resolved = graph.FindRuntimeDependencies(rid.Name, owner.Name).ToArray();
                if (resolved.Length != set.Dependencies.Count) throw new Exception("NuGet dependency lookup");
            }
        }
        if (edges != 97) throw new Exception("Total edges");
        var platforms = JsonRuntimeFormat.ReadRuntimeGraph(args[1]);
        var merged = RuntimeGraph.Merge(platforms, graph);
        foreach (var item in new[] {
            ("win7-x64", "System.Collections", "runtime.any.System.Collections"),
            ("win7-x64", "System.Console", "runtime.win.System.Console"),
            ("ubuntu.16.04-x64", "System.Console", "runtime.unix.System.Console"),
            ("osx.10.11-x64", "System.Collections", "runtime.any.System.Collections") })
        {
            if (!merged.FindRuntimeDependencies(item.Item1, item.Item2).Any(p => p.Id == item.Item3)) throw new Exception("Merged RID mapping: " + item);
            Console.WriteLine("PASS platform/Targets dependency lookup: " + item.Item1 + "/" + item.Item2 + " -> " + item.Item3);
        }
        Console.WriteLine("PASS all22 runtime rows/97 dependency ranges,14 support profiles and source Platforms1.1 merged lookups");
    }
}
