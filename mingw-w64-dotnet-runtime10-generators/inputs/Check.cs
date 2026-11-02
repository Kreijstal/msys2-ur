using System;
using System.Collections;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.Loader;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.Xml.Linq;
using Microsoft.CodeAnalysis.Host.Mef;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CodeActions;
using Microsoft.CodeAnalysis.CodeFixes;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Diagnostics;
using Microsoft.CodeAnalysis.Emit;
using Microsoft.CodeAnalysis.Text;

internal static class Check
{
    static void Require(bool value, string message) { if (!value) throw new Exception(message); }
    sealed class Config : AnalyzerConfigOptions
    {
        readonly string version;
        internal Config(string version) => this.version = version;
        public override bool TryGetValue(string key, out string value)
        {
            value = key switch {
                "build_property.TargetFrameworkIdentifier" => ".NETCoreApp",
                "build_property.TargetFrameworkVersion" => "v" + version,
                "build_property.TargetFramework" => "net" + version,
                "build_property.LibraryImportGenerator_UseMarshalType" => "true",
                _ => null,
            };
            return value != null;
        }
    }
    sealed class ConfigProvider : AnalyzerConfigOptionsProvider
    {
        readonly Config config;
        internal ConfigProvider(string version) => config = new(version);
        public override AnalyzerConfigOptions GlobalOptions => config;
        public override AnalyzerConfigOptions GetOptions(SyntaxTree tree) => config;
        public override AnalyzerConfigOptions GetOptions(AdditionalText textFile) => config;
    }
    static CSharpParseOptions Parse = new(LanguageVersion.Preview);
    static ImmutableArray<MetadataReference> References(string folder)
    {
        var files = Directory.GetFiles(folder, "*.dll");
        Require(files.Length >= 160, "Complete reference contract input: " + folder);
        Console.WriteLine("REFERENCE CONTRACT " + folder + " assemblies=" + files.Length);
        return files.Select(p => (MetadataReference)MetadataReference.CreateFromFile(p)).ToImmutableArray();
    }
    static CSharpCompilation Compilation(string name, string source, ImmutableArray<MetadataReference> refs, params SyntaxTree[] extra) =>
        CSharpCompilation.Create(name, new[] { CSharpSyntaxTree.ParseText(SourceText.From(source, Encoding.UTF8), Parse, "owned-π.cs") }.Concat(extra), refs,
            new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary, allowUnsafe: true, optimizationLevel: OptimizationLevel.Release, deterministic: true));
    static ISourceGenerator Generator(Type type) => Activator.CreateInstance(type) switch {
        IIncrementalGenerator incremental => incremental.AsSourceGenerator(),
        ISourceGenerator generator => generator,
        _ => throw new Exception(type.FullName),
    };
    static (CSharpCompilation compilation, GeneratorDriver driver, byte[] pe) Generate(string name, string text, ImmutableArray<MetadataReference> refs,
        string version, IEnumerable<Type> types, string output, params SyntaxTree[] extra)
    {
        var compilation = Compilation(name, text, refs, extra);
        GeneratorDriver driver = CSharpGeneratorDriver.Create(types.Select(Generator), parseOptions: Parse, optionsProvider: new ConfigProvider(version));
        driver = driver.RunGeneratorsAndUpdateCompilation(compilation, out var updated, out var diagnostics);
        foreach (var diagnostic in diagnostics) Console.WriteLine(name + ": " + diagnostic);
        Require(driver.GetRunResult().Results.All(r => r.Exception == null), name + " generator exception");
        Require(!diagnostics.Any(d => d.Severity == DiagnosticSeverity.Error), name + " generation diagnostics");
        Require(driver.GetRunResult().GeneratedTrees.Length > 0, name + " must generate real source");
        string folder = Path.Combine(output, name); Directory.CreateDirectory(folder);
        foreach (var result in driver.GetRunResult().Results)
            foreach (var source in result.GeneratedSources)
                File.WriteAllText(Path.Combine(folder, result.Generator.GetType().Name + "-" + source.HintName.Replace('/', '_').Replace('\\', '_')), source.SourceText.ToString());
        using var pe = new MemoryStream();
        var emitted = updated.Emit(pe);
        foreach (var diagnostic in emitted.Diagnostics.Where(d => d.Severity == DiagnosticSeverity.Error)) Console.WriteLine(diagnostic);
        Require(emitted.Success, name + " generated source compiles against actual source reference assemblies");
        File.WriteAllBytes(Path.Combine(folder, name + ".dll"), pe.ToArray());
        Console.WriteLine($"PASS {name}: {driver.GetRunResult().GeneratedTrees.Length} generated trees and emitted assembly");
        return ((CSharpCompilation)updated, driver, pe.ToArray());
    }
    static void Execute(byte[] bytes, string type, string method, object expected, params string[] dependencies)
    {
        var context = new AssemblyLoadContext("generated-owned-" + Guid.NewGuid(), true);
        var paths = dependencies.ToDictionary(p => Path.GetFileNameWithoutExtension(p), StringComparer.OrdinalIgnoreCase);
        context.Resolving += (load, name) => paths.TryGetValue(name.Name, out var path) ? load.LoadFromAssemblyPath(Path.GetFullPath(path)) : null;

        try {
            var assembly = context.LoadFromStream(new MemoryStream(bytes));
            Require(Equals(assembly.GetType(type).GetMethod(method).Invoke(null, null), expected), type + "." + method + " executed result");
        } finally { context.Unload(); }
    }
    static string[] AttributeNames(Type type) => type.GetCustomAttributesData().Select(a => a.AttributeType.FullName).ToArray();
    static void SourceInventory(string output, string root, JsonElement projects, Dictionary<string, Assembly> assemblies)
    {
        foreach (var project in projects.EnumerateObject()) {
            string defines = XDocument.Load(Path.Combine(output, project.Name, "Build.csproj")).Descendants("DefineConstants").Single().Value;
            var parse = Parse.WithPreprocessorSymbols(defines.Split(';', StringSplitOptions.RemoveEmptyEntries));
            foreach (var kind in new[] { ("Generator", "Microsoft.CodeAnalysis.GeneratorAttribute"), ("DiagnosticAnalyzer", "Microsoft.CodeAnalysis.Diagnostics.DiagnosticAnalyzerAttribute"), ("ExportCodeFixProvider", "Microsoft.CodeAnalysis.CodeFixes.ExportCodeFixProviderAttribute") }) {
                var expected = new HashSet<string>();
                foreach (var file in project.Value.GetProperty("original_cs").EnumerateObject()) {
                    var tree = CSharpSyntaxTree.ParseText(File.ReadAllText(Path.Combine(root, "r", file.Name)), parse);
                    foreach (var node in tree.GetRoot().DescendantNodes().OfType<ClassDeclarationSyntax>()) {
                        if (!node.AttributeLists.SelectMany(a => a.Attributes).Any(a => a.Name.ToString().Split('.').Last().TrimEnd() == kind.Item1)) continue;
                        string name = string.Join(".", node.AncestorsAndSelf().Reverse().Select(n => n switch { BaseNamespaceDeclarationSyntax ns => ns.Name.ToString(), ClassDeclarationSyntax cls => cls.Identifier.ValueText, _ => null }).Where(n => n != null));
                        expected.Add(name);
                    }
                }
                var actual = assemblies[project.Name].GetTypes().Where(t => AttributeNames(t).Contains(kind.Item2)).Select(t => t.FullName).ToHashSet();
                Require(expected.SetEquals(actual), project.Name + " complete source " + kind.Item1 + " inventory");
            }
        }
        Console.WriteLine("PASS every generator/analyzer/codefix entry point matches original active source declarations");
    }

    static void Resources(string manifest, Dictionary<string, Assembly> assemblies)
    {
        using var entries = JsonDocument.Parse(File.ReadAllText(manifest));
        int sets = 0, strings = 0;
        foreach (var entry in entries.RootElement.EnumerateArray()) {
            var assembly = assemblies[entry.GetProperty("assembly").GetString()];
            string culture = entry.GetProperty("culture").GetString();
            if (culture.Length != 0) {
                string satellite = Path.Combine(Path.GetDirectoryName(assembly.Location), culture, assembly.GetName().Name + ".resources.dll");
                assembly = AssemblyLoadContext.Default.LoadFromAssemblyPath(Path.GetFullPath(satellite));
            }
            string name = entry.GetProperty("resource").GetString() + (culture.Length == 0 ? "" : "." + culture) + ".resources";
            using var reader = new ResourceReader(assembly.GetManifestResourceStream(name) ?? throw new Exception(name));
            var actual = reader.Cast<DictionaryEntry>().ToDictionary(e => (string)e.Key, e => (string)e.Value);
            Require(actual.Count == entry.GetProperty("strings").EnumerateObject().Count(), name);
            foreach (var value in entry.GetProperty("strings").EnumerateObject()) { Require(actual[value.Name] == value.Value.GetString(), name + "/" + value.Name); strings++; }
            sets++;
        }
        Console.WriteLine($"PASS all {sets} original generator resource sets / {strings} values");
    }
    static async Task Main(string[] args)
    {
        string output = args[0], root = args[1], refs10 = args[2], refs8 = args[3];
        using var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(output, "source-inputs.json")));
        var assemblies = new Dictionary<string, Assembly>();
        foreach (var entry in manifest.RootElement.GetProperty("projects").EnumerateObject()) {
            string path = Path.GetFullPath(args.Length == 7 ? Path.Combine(args[6], entry.Name + ".dll") : Path.Combine(output, entry.Name, "bin/Release/netstandard2.0", entry.Name + ".dll"));
            assemblies.Add(entry.Name, AssemblyLoadContext.Default.LoadFromAssemblyPath(path));
        }
        foreach (var entry in assemblies) {
            var assembly = entry.Value;
            Require(assembly.GetName().Version == new Version(10, 0, 0, 0), entry.Key + " version");
            Require(assembly.GetCustomAttribute<global::System.Runtime.Versioning.TargetFrameworkAttribute>().FrameworkName == ".NETStandard,Version=v2.0", entry.Key + " framework");
            Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion == "10.0.5+081d220c0a773ffb7c6bea6b48727833576a65ef", entry.Key + " source commit");
            Require(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>().Version == "10.0.526.11800", entry.Key + " source file version");
            string key = manifest.RootElement.GetProperty("projects").GetProperty(entry.Key).GetProperty("key_policy").GetProperty("key").GetString();
            Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant() == (key == "Microsoft" ? "b03f5f7f11d50a3a" : "cc7b13ffcd2ddd51"), entry.Key + " signing identity");
        }
        Resources(Path.Combine(output, "localization.json"), assemblies);
        SourceInventory(output, root, manifest.RootElement.GetProperty("projects"), assemblies);
        var generatorTypes = assemblies.Values.SelectMany(a => a.GetTypes()).Where(t => AttributeNames(t).Contains("Microsoft.CodeAnalysis.GeneratorAttribute")).ToArray();
        var analyzerTypes = assemblies.Values.SelectMany(a => a.GetTypes()).Where(t => AttributeNames(t).Contains("Microsoft.CodeAnalysis.Diagnostics.DiagnosticAnalyzerAttribute")).ToArray();
        var fixTypes = assemblies.Values.SelectMany(a => a.GetTypes()).Where(t => AttributeNames(t).Contains("Microsoft.CodeAnalysis.CodeFixes.ExportCodeFixProviderAttribute")).ToArray();
        foreach (var type in generatorTypes) Console.WriteLine("GENERATOR " + type.FullName);
        foreach (var type in analyzerTypes) Require(Activator.CreateInstance(type) is DiagnosticAnalyzer, type.FullName);
        foreach (var type in fixTypes) Require(Activator.CreateInstance(type) is CodeFixProvider, type.FullName);
        Require(generatorTypes.Length == 8, "All eight original generator entry points");
        var reference10 = References(refs10); var reference8 = References(refs8);
        string generated = Path.Combine(args[4], "generated"); Directory.CreateDirectory(generated);
        Type[] In(string assembly) => generatorTypes.Where(t => t.Assembly == assemblies[assembly]).ToArray();
        const string imports = "using System.Runtime.InteropServices; public static partial class Native { [LibraryImport(\"kernel32.dll\")] public static partial uint GetCurrentProcessId(); public static int Run() => checked((int)GetCurrentProcessId()); }";
        Generate("LibraryImport10", imports, reference10, "10.0", In("Microsoft.Interop.LibraryImportGenerator"), generated);
        var native8 = Generate("LibraryImport8", imports, reference8, "8.0", In("Microsoft.Interop.LibraryImportGenerator"), generated);
        Execute(native8.pe, "Native", "Run", Environment.ProcessId);
        const string com = "using System; using System.Runtime.InteropServices; using System.Runtime.InteropServices.Marshalling; [GeneratedComInterface, Guid(\"8154C11F-357A-4F8A-9C83-8DDBB7741F28\")] public partial interface ICalc { int Add(int a,int b); } [GeneratedComClass] public partial class Calc : ICalc { public int Add(int a,int b)=>a+b; }";
        var comResult = Generate("Com10", com, reference10, "10.0", In("Microsoft.Interop.ComInterfaceGenerator"), generated);
        Require(comResult.driver.GetRunResult().Results.Count(r => r.GeneratedSources.Length > 0) == 2, "COM interface and class generators both produced source");
        string ancillary = Path.Combine(root, "r/src/libraries/System.Runtime.InteropServices/tests/Ancillary.Interop");
        var extra = Directory.GetFiles(ancillary, "*.cs").Concat(new[] { Path.Combine(root, "r/src/libraries/System.Runtime.InteropServices/tests/Common/MarshalDirection.cs"), Path.Combine(root, "r/src/libraries/System.Runtime.InteropServices/tests/Common/ExceptionMarshalling.cs") })
            .Select(p => CSharpSyntaxTree.ParseText(SourceText.From(File.ReadAllText(p), Encoding.UTF8), Parse.WithPreprocessorSymbols("ANCILLARY_INTEROP"), p)).ToArray();
        const string vtable = "using System.Runtime.InteropServices.Marshalling; [UnmanagedObjectUnwrapper<UnmanagedObjectUnwrapper.TestUnwrapper>] partial interface INativeAPI : IUnmanagedInterfaceType { static unsafe void* IUnmanagedInterfaceType.VirtualMethodTableManagedImplementation => null; [VirtualMethodIndex(0)] void Method(); }";
        Generate("Vtable10", vtable, reference10, "10.0", generatorTypes.Where(t => t.Name == "VtableIndexStubGenerator"), generated, extra);
        const string javascript = "using System.Runtime.InteropServices.JavaScript; public static partial class JS { [JSImport(\"Math.abs\",\"globalThis\")] public static partial double Abs(double value); [JSExport] public static int Add(int a,int b)=>a+b; }";
        var js = Generate("JavaScript10", javascript, reference10, "10.0", In("Microsoft.Interop.JavaScript.JSImportGenerator"), generated);
        Require(js.driver.GetRunResult().Results.All(r => r.GeneratedSources.Length > 0), "JS import and export generators both produced source");
        const string json = "using System.Text.Json; using System.Text.Json.Serialization; public sealed class Payload { public string Name {get;set;} = \"\"; public int Value {get;set;} } [JsonSerializable(typeof(Payload))] public partial class JsonContext : JsonSerializerContext {} public static class JsonProbe { public static int Run() {var value=new Payload{Name=\"π\",Value=42}; string text=JsonSerializer.Serialize(value,JsonContext.Default.Payload); var restored=JsonSerializer.Deserialize(text,JsonContext.Default.Payload); return restored.Name==value.Name&&JsonContext.Default.Payload.Properties.Count==2 ? restored.Value : -1;}}";
        Generate("Json10", json, reference10, "10.0", In("System.Text.Json.SourceGeneration"), generated);
        var jsonDependencies = new[] { "System.Text.Json", "System.Text.Encodings.Web", "System.IO.Pipelines" }
            .Select(n => Path.Combine(args[5], n, "bin/Release/net8.0", n + ".dll")).ToArray();
        var jsonNames = jsonDependencies.Select(Path.GetFileName).ToHashSet(StringComparer.OrdinalIgnoreCase);
        var jsonReferences = reference8.Where(r => !jsonNames.Contains(Path.GetFileName(r.Display)))
            .Concat(jsonDependencies.Select(p => (MetadataReference)MetadataReference.CreateFromFile(p))).ToImmutableArray();
        var json8 = Generate("Json10On8", json, jsonReferences, "8.0", In("System.Text.Json.SourceGeneration"), generated);
        Execute(json8.pe, "JsonProbe", "Run", 42, jsonDependencies);
        const string regex = "using System.Text.RegularExpressions; public static partial class RegexProbe { [GeneratedRegex(\"^[A-Z]{2}[0-9]{3}$\",RegexOptions.CultureInvariant,1000)] private static partial Regex Match(); public static bool Run()=>Match().IsMatch(\"AB123\")&&!Match().IsMatch(\"ab123\")&&!Match().IsMatch(\"AB12\"); }";
        Generate("Regex10", regex, reference10, "10.0", In("System.Text.RegularExpressions.Generator"), generated);
        var regex8 = Generate("Regex8", regex, reference8, "8.0", In("System.Text.RegularExpressions.Generator"), generated);
        Execute(regex8.pe, "RegexProbe", "Run", true);
        foreach (var pair in new[] { ("BadRegex", "using System.Text.RegularExpressions; partial class Broken { [GeneratedRegex(\"[\")] private static partial Regex R(); }", "System.Text.RegularExpressions.Generator"), ("BadImport", "using System.Runtime.InteropServices; partial class Broken { [LibraryImport(\"kernel32\")] public static int F()=>0; }", "Microsoft.Interop.LibraryImportGenerator") }) {
            GeneratorDriver driver = CSharpGeneratorDriver.Create(In(pair.Item3).Select(Generator), parseOptions: Parse, optionsProvider: new ConfigProvider("10.0"));
            driver = driver.RunGeneratorsAndUpdateCompilation(Compilation(pair.Item1, pair.Item2, reference10), out _, out var diagnostics);
            Require(driver.GetRunResult().Results.All(r => r.Exception == null) && diagnostics.Any(d => d.Severity == DiagnosticSeverity.Error), pair.Item1 + " original generator diagnostics");
        }
        var analyzerCompilation = Compilation("AnalyzerProbe", "using System.Runtime.InteropServices; using System.Text.RegularExpressions; class Probe { [DllImport(\"kernel32.dll\")] static extern uint GetCurrentProcessId(); public bool Match(string text)=>new Regex(\"abc\").IsMatch(text); }", reference10);
        var analyzers = analyzerTypes.Select(t => (DiagnosticAnalyzer)Activator.CreateInstance(t)).ToImmutableArray();
        var analyzerDiagnostics = await analyzerCompilation.WithAnalyzers(analyzers).GetAnalyzerDiagnosticsAsync();
        Require(!analyzerDiagnostics.Any(d => d.Id == "AD0001"), "Original analyzers run without exceptions");
        Require(analyzerDiagnostics.Any(d => d.Id == "SYSLIB1054") && analyzerDiagnostics.Any(d => d.Id == "SYSLIB1045"), "Actual import/regex analyzer callbacks");
        using (var workspace = new AdhocWorkspace(MefHostServices.Create(new[] { typeof(Workspace).Assembly, typeof(Microsoft.CodeAnalysis.CSharp.Formatting.CSharpFormattingOptions).Assembly }))) {
            var project = workspace.AddProject("RegexFix", LanguageNames.CSharp).WithMetadataReferences(reference10)
                .WithCompilationOptions(new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary)).WithParseOptions(Parse);
            var document = workspace.AddDocument(project.Id, "fix.cs", SourceText.From("using System.Text.RegularExpressions; public class RegexFix { public bool Match(string text)=>new Regex(\"abc\").IsMatch(text); }", Encoding.UTF8));
            // Apply the complete project's reference and parse settings to the document solution.
            var configured = document.Project.Solution.WithProjectMetadataReferences(project.Id, reference10).WithProjectParseOptions(project.Id, Parse).WithProjectCompilationOptions(project.Id, new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));
            Require(workspace.TryApplyChanges(configured), "Apply codefix project references");
            document = workspace.CurrentSolution.GetDocument(document.Id);
            var compilation = await document.Project.GetCompilationAsync();
            var diagnostics = await compilation.WithAnalyzers(analyzers).GetAnalyzerDiagnosticsAsync();
            var diagnostic = diagnostics.Single(d => d.Id == "SYSLIB1045");
            var fixer = (CodeFixProvider)Activator.CreateInstance(fixTypes.Single(t => t.Name == "UpgradeToGeneratedRegexCodeFixer"));
            var actions = new List<CodeAction>();
            await fixer.RegisterCodeFixesAsync(new CodeFixContext(document, diagnostic, (action, _) => actions.Add(action), CancellationToken.None));
            Require(actions.Count > 0, "Real regex codefix registration");
            foreach (var operation in await actions[0].GetOperationsAsync(CancellationToken.None)) operation.Apply(workspace, CancellationToken.None);
            string fixedText = (await workspace.CurrentSolution.GetDocument(document.Id).GetTextAsync()).ToString();
            Require(fixedText.Contains("GeneratedRegex"), "Real regex codefix applies source-generation attribute");
            Generate("RegexCodeFix10", fixedText, reference10, "10.0", In("System.Text.RegularExpressions.Generator"), generated);
        }
        Console.WriteLine($"PASS all eight generators, {analyzerTypes.Length} analyzers, {fixTypes.Length} codefix providers, invalid input diagnostics, .NET10 emit and .NET8 generated-code execution");
        File.WriteAllText(Path.Combine(args[4], "results.json"), JsonSerializer.Serialize(new { generator_entry_points = generatorTypes.Select(t => t.FullName), analyzer_types = analyzerTypes.Select(t => t.FullName), codefix_types = fixTypes.Select(t => t.FullName), net10_generated_code_compiles = true, native_import_json_regex_net8_execution = true, json10_net8_implementation_executed = true, javascript_browser_execution = false, net10_full_framework_execution = false, full_dependency_goal_complete = false }, new JsonSerializerOptions { WriteIndented = true }));
    }
}
