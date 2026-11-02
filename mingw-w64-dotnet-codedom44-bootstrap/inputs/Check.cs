using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.Loader;
using System.Text.Json;
using Mono.Cecil;

sealed class OwnedContext : AssemblyLoadContext
{
    readonly string directory;
    public OwnedContext(string directory) : base(isCollectible: true) { this.directory = directory; }
    protected override Assembly? Load(AssemblyName name) => name.Name == "System.CodeDom" ? LoadFromAssemblyPath(Path.Combine(directory, "System.CodeDom.dll")) : null;
}
static class Program
{
    static void Require(bool value, string name) { if (!value) throw new Exception(name); }
    static void Main(string[] args)
    {
        var directory = Path.GetFullPath(args[0]);
        using var baseline = JsonDocument.Parse(File.ReadAllText(args[1]));
        using var sources = JsonDocument.Parse(File.ReadAllText(args[2]));
        var expected = baseline.RootElement.GetProperty("System.CodeDom.dll");
        var path = Path.Combine(directory, "System.CodeDom.dll");
        var api = expected.GetProperty("api").EnumerateArray().Select(x => x.GetString()!).ToArray();
        var actual = Api.Read(path);
        File.WriteAllLines(Path.Combine(directory, "missing-api.txt"), api.Except(actual));
        File.WriteAllLines(Path.Combine(directory, "extra-api.txt"), actual.Except(api));
        Require(api.SequenceEqual(actual), "original CodeDom public API mismatch");
        using var assembly = AssemblyDefinition.ReadAssembly(path);
        Require(assembly.Name.FullName == expected.GetProperty("identity").GetString(), "original identity");
        Require(assembly.MainModule.AssemblyReferences.Select(x => x.FullName).SequenceEqual(expected.GetProperty("references").EnumerateArray().Select(x => x.GetString()!)), "original runtime dependency table");
        Require(!assembly.CustomAttributes.Any(a => a.AttributeType.FullName == "System.Runtime.Versioning.TargetFrameworkAttribute"), "original no TFM attribute policy");
        Require((string)assembly.CustomAttributes.Single(a => a.AttributeType.FullName == "System.Reflection.AssemblyFileVersionAttribute").ConstructorArguments[0].Value == "4.6.25519.03", "original file version");
        using var refBaseline = JsonDocument.Parse(File.ReadAllText(args[3]));
        var refExpected = refBaseline.RootElement.GetProperty("System.CodeDom.dll");
        var refPath = Path.Combine(directory, "reference/System.CodeDom.dll");
        var refApi = refExpected.GetProperty("api").EnumerateArray().Select(x => x.GetString()!).ToArray();
        var refActual = Api.Read(refPath);
        File.WriteAllLines(Path.Combine(directory, "missing-ref-api.txt"), refApi.Except(refActual));
        File.WriteAllLines(Path.Combine(directory, "extra-ref-api.txt"), refActual.Except(refApi));
        Require(refApi.SequenceEqual(refActual), "original CodeDom compiler reference API mismatch");
        using var reference = AssemblyDefinition.ReadAssembly(refPath);
        Require(reference.Name.FullName == refExpected.GetProperty("identity").GetString(), "original compiler reference identity");
        Require(reference.MainModule.AssemblyReferences.Select(x => x.FullName).SequenceEqual(refExpected.GetProperty("references").EnumerateArray().Select(x => x.GetString()!)), "original compiler reference dependency table");
        Require(reference.CustomAttributes.Any(a => a.AttributeType.FullName == "System.Runtime.CompilerServices.ReferenceAssemblyAttribute"), "reference-only compiler contract");
        var embedded = assembly.MainModule.Resources.OfType<EmbeddedResource>().ToArray();
        Require(embedded.Length == 1 && embedded[0].Name == "FxResources.System.CodeDom.SR.resources", "resource identity");
        using var reader = new ResourceReader(embedded[0].GetResourceStream());
        var values = reader.Cast<DictionaryEntry>().ToDictionary(e => (string)e.Key, e => (string)e.Value!);
        var resources = sources.RootElement.GetProperty("resources");
        Require(values.Count == resources.EnumerateObject().Count(), "resource count");
        foreach (var item in resources.EnumerateObject()) Require(values[item.Name] == item.Value.GetString(), "resource " + item.Name);
        var context = new OwnedContext(directory);
        var bridge = context.LoadFromAssemblyPath(Path.Combine(directory, "Bridge.dll"));
        Console.WriteLine(bridge.GetType("Bridge")!.GetMethod("Run")!.Invoke(null, new object[] { directory }));
        Require(context.Assemblies.Single(a => a.GetName().Name == "System.CodeDom").Location == path, "must execute exact candidate CodeDom");
        context.Unload();
        Console.WriteLine($"PASS {api.Length} original runtime and {refApi.Length} original reference API entries, exact dependency tables and {values.Count} original resource values");
    }
}
