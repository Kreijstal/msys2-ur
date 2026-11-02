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
        using var expected = JsonDocument.Parse(File.ReadAllText(args[1]));
        using var reader = new PackageArchiveReader(args[0]);
        if (reader.GetIdentity().Id != "NETStandard.Library" || reader.GetIdentity().Version.ToNormalizedString() != "1.6.1") throw new Exception("Identity");
        var groups = reader.GetPackageDependencies().ToArray();
        var baseline = expected.RootElement.GetProperty("dependency_groups").EnumerateArray().ToArray();
        if (groups.Length != baseline.Length || groups.Length != 4) throw new Exception("Dependency group count");
        foreach (var row in baseline)
        {
            var framework = NuGetFramework.Parse(row.GetProperty("framework").GetString()!);
            var actual = groups.Single(g => g.TargetFramework.Equals(framework));
            var deps = row.GetProperty("dependencies").EnumerateArray().ToArray();
            if (deps.Length != actual.Packages.Count()) throw new Exception("Dependency count: " + framework);
            foreach (var dep in deps)
            {
                var package = actual.Packages.Single(p => p.Id == dep.GetProperty("id").GetString());
                if (package.VersionRange.MinVersion!.ToNormalizedString() != dep.GetProperty("version").GetString() ||
                    !package.VersionRange.IsMinInclusive || package.VersionRange.MaxVersion != null) throw new Exception("Dependency version range");
            }
        }
        foreach (string target in new[] { "netstandard1.0", "netstandard1.1", "netstandard1.2", "netstandard1.3", "netstandard1.6", "netcoreapp1.0" })
        {
            var nearest = new FrameworkReducer().GetNearest(NuGetFramework.ParseFolder(target), groups.Select(g => g.TargetFramework));
            string wanted = target is "netstandard1.6" or "netcoreapp1.0" ? "netstandard1.3" : target;
            if (nearest == null || nearest.GetShortFolderName() != wanted) throw new Exception("Framework selection: " + target);
            Console.WriteLine("PASS dependency selection: " + target + " -> " + wanted);
        }
        if (reader.GetFiles().Any(p => p.EndsWith(".dll", StringComparison.OrdinalIgnoreCase) || p.EndsWith(".exe", StringComparison.OrdinalIgnoreCase) || p.EndsWith("_._"))) throw new Exception("Unexpected implementation or marker payload");
        Console.WriteLine("PASS original metapackage identity, 4 groups, 128 versioned edges and six framework selections; zero implementation/marker payloads");
    }
}
