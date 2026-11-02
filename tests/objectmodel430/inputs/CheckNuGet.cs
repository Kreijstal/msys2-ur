using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using NuGet.Frameworks;
using NuGet.Packaging;

static class Program
{
    static void Main(string[] args)
    {
        using var reader = new PackageArchiveReader(args[0]);
        using var policy = JsonDocument.Parse(File.ReadAllText(args[1]));
        string name = reader.GetIdentity().Id;
        if (reader.GetIdentity().Version.ToNormalizedString() != "4.3.0") throw new Exception("Original version");
        var baseline = policy.RootElement.GetProperty(name);
        var groups = reader.GetPackageDependencies().ToArray();
        var expected = baseline.GetProperty("dependencies").EnumerateArray().ToArray();
        if (groups.Length != expected.Length) throw new Exception("Dependency groups");
        foreach (var row in expected)
        {
            var group = groups.Single(g => g.TargetFramework.Equals(NuGetFramework.Parse(row.GetProperty("framework").GetString()!)));
            var deps = row.GetProperty("dependencies").EnumerateArray().ToArray();
            if (group.Packages.Count() != deps.Length) throw new Exception("Dependency count");
            foreach (var dep in deps)
            {
                var actual = group.Packages.Single(d => d.Id == dep.GetProperty("id").GetString());
                if (actual.VersionRange.MinVersion!.ToNormalizedString() != dep.GetProperty("version").GetString() || !actual.VersionRange.IsMinInclusive || actual.VersionRange.MaxVersion != null) throw new Exception("Dependency range");
                string[] wantedExclude=dep.TryGetProperty("exclude",out var exclude)?exclude.GetString()!.Split(',',';').OrderBy(v=>v,StringComparer.OrdinalIgnoreCase).ToArray():Array.Empty<string>();
                if(!actual.Exclude.OrderBy(v=>v,StringComparer.OrdinalIgnoreCase).SequenceEqual(wantedExclude,StringComparer.OrdinalIgnoreCase)) throw new Exception("Original dependency exclude scope: "+actual.Id);
                if(actual.Include.Any()) throw new Exception("Unexpected dependency include scope: "+actual.Id);
            }
        }
        var originalFiles = baseline.GetProperty("reference_DLL_sha256").EnumerateObject().Select(p => p.Name).Concat(baseline.GetProperty("original_data_sha256").EnumerateObject().Select(p => p.Name)).Where(p => p.StartsWith("ref/")).ToArray();
        var originalGroups = originalFiles.Select(p => NuGetFramework.ParseFolder(p.Split('/')[1])).Distinct().ToArray();
        var actualGroups = reader.GetItems("ref").ToArray();
        var reducer = new FrameworkReducer();
        foreach (string target in new[] { "netstandard1.0", "netstandard1.1", "netstandard1.2", "netstandard1.3", "netstandard1.6", "net8.0", "netcore50", "net45", "net46", "net462", "win8" })
        {
            var framework = NuGetFramework.ParseFolder(target);
            var wanted = reducer.GetNearest(framework, originalGroups);
            var actual = reducer.GetNearest(framework, actualGroups.Select(g => g.TargetFramework));
            if (!(wanted?.Equals(actual) ?? actual == null)) throw new Exception("Original framework selection: " + target);
            if (actual != null)
            {
                // NuGet consumes _._ as an empty framework group; the archive audit
                // independently verifies the original marker paths and bytes.
                var items = actualGroups.Single(g => g.TargetFramework.Equals(actual)).Items.Where(p => p.EndsWith(".dll")).OrderBy(p => p).ToArray();
                var wantedItems = originalFiles.Where(p => NuGetFramework.ParseFolder(p.Split('/')[1]).Equals(actual) && p.EndsWith(".dll")).OrderBy(p => p).ToArray();
                if (!items.SequenceEqual(wantedItems)) throw new Exception("Exact original framework assets: " + target + " actual=" + string.Join(";", items) + " expected=" + string.Join(";", wantedItems));
            }
        }
        var allowed = baseline.GetProperty("reference_DLL_sha256").EnumerateObject().Select(p => p.Name).OrderBy(p => p).ToArray();
        var dlls = reader.GetFiles().Where(p => p.EndsWith(".dll")).OrderBy(p => p).ToArray();
        if (!dlls.SequenceEqual(allowed)) throw new Exception("Original DLL asset paths");
        foreach (string target in new[] { "netstandard1.0", "netstandard1.3", "net8.0", "net46", "net462" })
        {
            var originalLib = allowed.Where(p => p.StartsWith("lib/")).Concat(baseline.GetProperty("original_data_sha256").EnumerateObject().Select(p => p.Name).Where(p => p.StartsWith("lib/"))).ToArray();
            var expectedLib = reducer.GetNearest(NuGetFramework.ParseFolder(target), originalLib.Select(p => NuGetFramework.ParseFolder(p.Split('/')[1])).Distinct());
            var actualLib = reducer.GetNearest(NuGetFramework.ParseFolder(target), reader.GetItems("lib").Select(g => g.TargetFramework));
            if (!(expectedLib?.Equals(actualLib) ?? actualLib == null)) throw new Exception("Runtime asset selection " + target);
            if (actualLib != null)
            {
                var actualItems = reader.GetItems("lib").Single(g => g.TargetFramework.Equals(actualLib)).Items.Where(p => p.EndsWith(".dll")).OrderBy(p => p);
                var expectedItems = originalLib.Where(p => NuGetFramework.ParseFolder(p.Split('/')[1]).Equals(actualLib) && p.EndsWith(".dll")).OrderBy(p => p);
                if (!actualItems.SequenceEqual(expectedItems)) throw new Exception("Exact runtime assets " + target);
            }
        }
        var frameworkAssemblies=reader.GetFrameworkItems().ToArray();
        var originalFrameworkAssemblies=baseline.GetProperty("framework_assemblies").EnumerateArray().ToArray();
        if(frameworkAssemblies.Sum(g=>g.Items.Count())!=originalFrameworkAssemblies.Length) throw new Exception("Framework assembly count");
        foreach(var original in originalFrameworkAssemblies)
        {
            var framework=NuGetFramework.Parse(original.GetProperty("targetFramework").GetString()!);
            var group=frameworkAssemblies.Single(g=>g.TargetFramework.Equals(framework));
            if(!group.Items.Contains(original.GetProperty("assemblyName").GetString()!))throw new Exception("Framework assembly identity");
        }
        Console.WriteLine("PASS original dependency groups/ranges and eleven compile and five runtime framework selections: " + name);
    }
}
