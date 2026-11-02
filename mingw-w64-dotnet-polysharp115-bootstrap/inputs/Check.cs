using System;
using System.Collections.Immutable;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.PortableExecutable;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using PolySharp.SourceGenerators;

static class Program
{
    static void Require(bool condition, string message)
    {
        if (!condition) throw new Exception(message);
    }
    static void Main(string[] args)
    {
        var assembly = typeof(PolyfillsGenerator).Assembly;
        Require(assembly.GetName().Version == new Version(1,15,0,0), "Original assembly identity");
        Require(assembly.GetCustomAttribute<System.Runtime.Versioning.TargetFrameworkAttribute>()!.FrameworkName == ".NETStandard,Version=v2.0", "Original generator target");
        Require(assembly.ManifestModule.GetCustomAttributesData().Any(a => a.AttributeType.FullName == "System.Runtime.CompilerServices.SkipLocalsInitAttribute"), "Generated module attribute");
        using (var pe = new PEReader(File.OpenRead(assembly.Location)))
            Require(pe.ReadDebugDirectory().Any(e => e.Type == DebugDirectoryEntryType.EmbeddedPortablePdb), "Original reproducibility tool embedded PDB");
        using var resources = JsonDocument.Parse(File.ReadAllText(args[1]));
        Require(assembly.GetManifestResourceNames().Length == 56, "Embedded source count");
        foreach (var property in resources.RootElement.EnumerateObject())
        {
            using var stream = assembly.GetManifestResourceStream(property.Name)!;
            Require(stream != null && Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant() == property.Value.GetString(), "Original embedded bytes: " + property.Name);
        }
        Require(typeof(Compilation).Assembly.GetName().Version == new Version(4,3,0,0), "Minimum Roslyn4.3 host");
        var refs = Directory.GetFiles(args[0], "*.dll").Select(p => MetadataReference.CreateFromFile(p)).ToArray();
        var options = new CSharpParseOptions(LanguageVersion.Preview);
        var tree = CSharpSyntaxTree.ParseText("""
            public record Entry(int Value);
            public class RequiredData { public required string Name { get; init; } }
            public static class Probe {
                public static int Run() {
                    var value = new RequiredData { Name = "owned" };
                    var range = new System.Range(1, new System.Index(1, true)).GetOffsetAndLength(5);
                    return new Entry(38).Value + range.Offset + range.Length;
                }
            }
            """, options, encoding:Encoding.UTF8);
        var input = CSharpCompilation.Create("PolySharpOwnedProbe", new[] { tree }, refs,
            new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary, nullableContextOptions:NullableContextOptions.Enable));
        Require(input.GetDiagnostics().Any(d => d.Severity == DiagnosticSeverity.Error), "Negative control must need polyfills");
        GeneratorDriver driver = CSharpGeneratorDriver.Create(new[] { new PolyfillsGenerator().AsSourceGenerator() }, parseOptions:options);
        driver = driver.RunGeneratorsAndUpdateCompilation(input, out var output, out var diagnostics);
        Require(diagnostics.IsEmpty, string.Join("\n", diagnostics));
        Require(driver.GetRunResult().GeneratedTrees.Length > 10, "Missing generated polyfills");
        using var bytes = new MemoryStream();
        var result = output.Emit(bytes);
        Require(result.Success, string.Join("\n", result.Diagnostics));
        bytes.Position = 0;
        var loaded = AssemblyLoadContext.Default.LoadFromStream(bytes);
        Require((int)loaded.GetType("Probe")!.GetMethod("Run")!.Invoke(null,null)! == 42, "Generated records/required members/range behavior");
        var oldOptions = new CSharpParseOptions(LanguageVersion.CSharp7_3);
        var oldInput = input.WithOptions(input.Options.WithNullableContextOptions(NullableContextOptions.Disable))
            .RemoveAllSyntaxTrees().AddSyntaxTrees(CSharpSyntaxTree.ParseText("class Old {}", oldOptions));
        GeneratorDriver oldDriver = CSharpGeneratorDriver.Create(new[] { new PolyfillsGenerator().AsSourceGenerator() }, parseOptions:oldOptions);
        oldDriver = oldDriver.RunGeneratorsAndUpdateCompilation(oldInput, out var oldOutput, out var oldDiagnostics);
        Require(oldDiagnostics.IsEmpty && oldDriver.GetRunResult().GeneratedTrees.IsEmpty, "C#7 early-return empty-array ports");
        Require(!oldOutput.GetDiagnostics().Any(d => d.Severity == DiagnosticSeverity.Error), "C#7 empty-generation behavior");
        Console.WriteLine("PASS 56 original embedded sources, SkipLocalsInit, embedded PDB and original NS2 generator identity");
        Console.WriteLine("PASS actual Roslyn4.3 host generation, negative control, NS2 emit and execution of records/required members/ranges; generated trees=" + driver.GetRunResult().GeneratedTrees.Length);
        Console.WriteLine("PASS C#7 early-return collection ports produce no generated trees or generator failures");
    }
}
