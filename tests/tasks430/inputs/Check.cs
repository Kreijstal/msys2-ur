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
        using var policy = JsonDocument.Parse(File.ReadAllText(args[1]));
        using var reader = new PackageArchiveReader(args[0]);
        string name = reader.GetIdentity().Id;
        var expected = policy.RootElement.GetProperty(name);
        if (reader.GetIdentity().Version.ToNormalizedString() != "4.3.0") throw new Exception("Version");
        var groups = reader.GetPackageDependencies().ToArray();
        var baseline = expected.GetProperty("dependencies").EnumerateArray().ToArray();
        if (groups.Length != baseline.Length) throw new Exception("Dependency groups");
        foreach (var row in baseline)
        {
            var framework = NuGetFramework.Parse(row.GetProperty("framework").GetString()!);
            var actual = groups.Single(g => g.TargetFramework.Equals(framework));
            var deps = row.GetProperty("dependencies").EnumerateArray().ToArray();
            if (deps.Length != actual.Packages.Count()) throw new Exception("Dependency count");
            foreach (var dep in deps)
            {
                var package = actual.Packages.Single(p => p.Id == dep.GetProperty("id").GetString());
                if (package.VersionRange.MinVersion!.ToNormalizedString() != dep.GetProperty("version").GetString() ||
                    !package.VersionRange.IsMinInclusive || package.VersionRange.MaxVersion != null) throw new Exception("Dependency range");
            }
        }
        var refs = reader.GetItems("ref").ToArray();
        foreach (string target in new[] { "netstandard1.0", "netstandard1.1", "netstandard1.3", "netstandard2.0", "netcore50", "net45", "win8" })
        {
            string wanted = target;
            if (target.StartsWith("netstandard")) wanted = target is "netstandard1.3" or "netstandard2.0" ? "netstandard1.3" : "netstandard1.0";
            var nearest = new FrameworkReducer().GetNearest(NuGetFramework.ParseFolder(target), refs.Select(g => g.TargetFramework));
            if (nearest == null || nearest.GetShortFolderName() != wanted) throw new Exception("Reference selection: " + target);
            var items = refs.Single(g => g.TargetFramework.Equals(nearest)).Items.ToArray();
            if (target is "net45" or "win8")
            {
                if (items.Any(i => i.EndsWith(".dll", StringComparison.OrdinalIgnoreCase))) throw new Exception("Framework marker");
            }
            else if (items.Count(i => i.EndsWith("/" + name + ".dll", StringComparison.Ordinal)) != 1) throw new Exception("Reference assembly selection");
            Console.WriteLine("PASS " + name + " reference selection: " + target + " -> " + wanted);
        }
        if (reader.GetFiles().Any(p => p.StartsWith("lib/") && p.EndsWith(".dll", StringComparison.OrdinalIgnoreCase))) throw new Exception("Runtime implementation");
        Console.WriteLine("PASS original NuGet dependency groups/ranges and seven framework reference selections: " + name);
    }
}
