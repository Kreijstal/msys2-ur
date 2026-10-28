using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Text.Json;
using System.Threading;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.FileSystemGlobbing;
using Microsoft.Extensions.FileSystemGlobbing.Abstractions;
using Microsoft.Extensions.Primitives;

static class Program
{
    static void Require(bool condition, string message)
    { if (!condition) throw new Exception(message); }
    static void Main(string[] args)
    {
        string directory = Path.GetFullPath(args[0]);
        using var expected = JsonDocument.Parse(File.ReadAllText(args[1]));
        var assemblies = new[] { typeof(StringValues).Assembly, typeof(IFileProvider).Assembly, typeof(Matcher).Assembly };
        int resourceValues = 0;
        foreach (var assembly in assemblies)
        {
            string name = assembly.GetName().Name;
            var baseline = expected.RootElement.EnumerateArray().Single(item => item.GetProperty("name").GetString() == name);
            Require(assembly.GetName().Version.ToString() == baseline.GetProperty("version").GetString(), "version " + name);
            Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant() == "adb9793829ddae60", "key " + name);
            Require(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>().Version == baseline.GetProperty("attributes").GetProperty("AssemblyFileVersionAttribute").GetString(), "file version " + name);
            Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion == baseline.GetProperty("attributes").GetProperty("AssemblyInformationalVersionAttribute").GetString(), "informational version " + name);
            Require(Path.GetDirectoryName(assembly.Location) == AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar), "foreign implementation " + name);
            var resources = baseline.GetProperty("resources");
            Require(assembly.GetManifestResourceNames().OrderBy(n => n).SequenceEqual(resources.EnumerateObject().Select(p => p.Name).OrderBy(n => n)), "resource manifests " + name);
            foreach (var resource in resources.EnumerateObject())
            {
                var manager = new ResourceManager(resource.Name[..^10], assembly);
                try
                {
                    var set = manager.GetResourceSet(CultureInfo.InvariantCulture, true, true);
                    Require(set.Cast<System.Collections.DictionaryEntry>().Count() == resource.Value.EnumerateObject().Count(), "resource count " + resource.Name);
                    foreach (var value in resource.Value.EnumerateObject())
                    {
                        Require(set.GetString(value.Name) == value.Value.GetString(), "resource value " + value.Name);
                        resourceValues++;
                    }
                }
                finally { manager.ReleaseAllResources(); }
            }
        }
        Require(resourceValues == 20, "complete resource value inventory");
        Console.WriteLine("PASS exact three source identities, six resource manifests and all20 original string values");

        var empty = default(StringValues);
        Require(empty.Count == 0 && empty.ToString() == "", "empty StringValues");
        var values = StringValues.Concat(new StringValues("λ"), new StringValues(new[] { "β", "gamma" }));
        Require(values.Count == 3 && values.SequenceEqual(new[] { "λ", "β", "gamma" }), "StringValues concatenation/enumeration");
        Require(values.ToString() == "λ,β,gamma" && StringValues.Equals(values, new[] { "λ", "β", "gamma" }), "StringValues conversion/equality");
        var segment = new StringSegment("aλβz", 1, 2);
        Require(segment.Value == "λβ" && segment.AsSpan().SequenceEqual("λβ"), "StringSegment Unicode slice");
        Require(segment.Subsegment(1, 1).Value == "β" && segment.IndexOf('β') == 1, "StringSegment ranges/search");
        Require(!default(StringSegment).HasValue && segment.Equals(new StringSegment("λβ")), "StringSegment identity");
        Require(string.Join("|", new StringTokenizer("a,,λ;b", new[] { ',', ';' }).Select(item => item.Value)) == "a||λ|b", "tokenizer empty/Unicode segments");
        int notifications = 0;
        using var first = new CancellationTokenSource();
        using var second = new CancellationTokenSource();
        using var third = new CancellationTokenSource();
        var current = first;
        using (var subscription = ChangeToken.OnChange(() => new CancellationChangeToken(current.Token), () => notifications++))
        {
            current = second; first.Cancel();
            current = third; second.Cancel();
            Require(notifications == 2, "change token resubscription");
        }
        third.Cancel(); Require(notifications == 2, "disposed subscription callback");
        using var compositeFirst = new CancellationTokenSource();
        using var compositeSecond = new CancellationTokenSource();
        var composite = new CompositeChangeToken(new IChangeToken[] { new CancellationChangeToken(compositeFirst.Token), new CancellationChangeToken(compositeSecond.Token) });
        int compositeCalls = 0;
        using (composite.RegisterChangeCallback(_ => compositeCalls++, null))
        {
            compositeFirst.Cancel(); compositeSecond.Cancel();
            Require(composite.HasChanged && compositeCalls == 1, "composite exactly-once notification");
        }
        Console.WriteLine("PASS source primitives: string/Unicode slices and values, tokenization, resubscription, composite notification and disposal");

        var provider = new NullFileProvider();
        var missing = provider.GetFileInfo("λ.txt");
        Require(!missing.Exists && missing.Name == "λ.txt" && missing.Length == -1 && missing.PhysicalPath == null && !missing.IsDirectory, "missing file contract");
        try { missing.CreateReadStream(); throw new Exception("missing stream did not throw"); }
        catch (FileNotFoundException) { }
        var contents = provider.GetDirectoryContents("directory");
        Require(!contents.Exists && !contents.Any(), "missing directory contract");
        var watch = provider.Watch("**/*"); int watchCalls = 0;
        using (watch.RegisterChangeCallback(_ => watchCalls++, null))
            Require(!watch.HasChanged && !watch.ActiveChangeCallbacks && watchCalls == 0, "null watch contract");
        Console.WriteLine("PASS source file provider abstractions: null files/directories/watch, Unicode name and missing-stream error");

        Directory.CreateDirectory(Path.Combine(directory, "sub"));
        foreach (var path in new[] { "a.txt", "README.TXT", "other.bin", "sub/λ.txt", "sub/skip.txt" })
            File.WriteAllText(Path.Combine(directory, path), "owned fixture λ");
        var matcher = new Matcher(StringComparison.OrdinalIgnoreCase).AddInclude("**/*.txt").AddExclude("sub/skip*");
        var actual = matcher.Execute(new DirectoryInfoWrapper(new DirectoryInfo(directory))).Files.Select(file => file.Path.Replace('\\', '/')).OrderBy(p => p).ToArray();
        Require(actual.SequenceEqual(new[] { "a.txt", "README.TXT", "sub/λ.txt" }.OrderBy(p => p)), "physical glob include/exclude/case/Unicode: " + string.Join(",", actual));
        var memory = matcher.Match(new[] { "a.txt", "sub/λ.txt", "sub/skip.txt", "other.bin" }).Files.Select(file => file.Path).OrderBy(p => p).ToArray();
        Require(memory.SequenceEqual(new[] { "a.txt", "sub/λ.txt" }.OrderBy(p => p)), "in-memory glob matching");
        var stem = new Matcher().AddInclude("src/**/*.cs").Match("src/deep/x.cs").Files.Single();
        Require(stem.Stem == "deep/x.cs", "recursive stem " + stem.Stem);
        Console.WriteLine("PASS source globbing: actual owned files, recursive includes/excludes, case/Unicode, in-memory matching and stems");
    }
}
