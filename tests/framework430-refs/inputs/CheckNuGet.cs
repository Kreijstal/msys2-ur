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
            }
        }
        var originalFiles = baseline.GetProperty("reference_DLL_sha256").EnumerateObject().Select(p => p.Name).Concat(baseline.GetProperty("original_data_sha256").EnumerateObject().Select(p => p.Name)).Where(p => p.StartsWith("ref/")).ToArray();
        var originalGroups = originalFiles.Select(p => NuGetFramework.ParseFolder(p.Split('/')[1])).Distinct().ToArray();
        var actualGroups = reader.GetItems("ref").ToArray();
        var reducer = new FrameworkReducer();
        foreach (string target in new[] { "netstandard1.0", "netstandard1.1", "netstandard1.2", "netstandard1.3", "netstandard1.6", "net8.0", "netcore50", "net45", "win8" })
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
        if (reader.GetFiles().Any(p => (p.StartsWith("lib/") || p.StartsWith("runtimes/")) && p.EndsWith(".dll"))) throw new Exception("Runtime provider substitution");
        Console.WriteLine("PASS original dependency groups/ranges and nine positive/negative framework selections: " + name);
    }
}
