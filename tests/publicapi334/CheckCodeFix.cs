using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CodeActions;
using Microsoft.CodeAnalysis.CodeFixes;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Formatting;
using Microsoft.CodeAnalysis.Diagnostics;
using Microsoft.CodeAnalysis.Host.Mef;
using Microsoft.CodeAnalysis.PublicApiAnalyzers;
using Microsoft.CodeAnalysis.Text;

internal static class Program
{
    static void Require(bool condition, string message) { if (!condition) throw new Exception(message); }
    static async Task Main(string[] args)
    {
        foreach (var assembly in new[] { typeof(DeclarePublicApiAnalyzer).Assembly, typeof(DeclarePublicApiFix).Assembly })
        {
            Require(assembly.GetName().Version!.ToString() == "3.3.8.6701", "original identity");
            Require(assembly.GetCustomAttribute<System.Runtime.Versioning.TargetFrameworkAttribute>()!.FrameworkName == ".NETStandard,Version=v2.0", "original NS2 profile");
            Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant() == "31bf3856ad364e35", "original public key");
            Require(assembly.Location == Path.Combine(AppContext.BaseDirectory, assembly.GetName().Name + ".dll"), "exact source DLL");
        }
        var host = MefHostServices.Create(MefHostServices.DefaultAssemblies.Add(typeof(CSharpFormattingOptions).Assembly).Distinct());
        using var workspace = new AdhocWorkspace(host);
        var project = workspace.AddProject("Fixture", LanguageNames.CSharp)
            .WithCompilationOptions(new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary, nullableContextOptions: NullableContextOptions.Enable))
            .AddMetadataReferences(Directory.GetFiles(args[0], "*.dll").Select(p => MetadataReference.CreateFromFile(p)));
        var original = project.AddDocument("Fixture.cs", SourceText.From("#nullable enable\npublic static class Fixture { public static string Echo(string value) => value; }\n"));
        project = original.Project.AddAdditionalDocument("PublicAPI.Shipped.txt", SourceText.From("#nullable enable\n"), filePath: Path.Combine(args[1], "PublicAPI.Shipped.txt")).Project;
        project = project.AddAdditionalDocument("PublicAPI.Unshipped.txt", SourceText.From("#nullable enable\n"), filePath: Path.Combine(args[1], "PublicAPI.Unshipped.txt")).Project;
        var analyzer = new DeclarePublicApiAnalyzer();
        var fixer = new DeclarePublicApiFix();
        int applied = 0;
        for (int pass = 0; pass < 5; pass++)
        {
            var additional = new List<AdditionalText>();
            foreach (var file in project.AdditionalDocuments)
                additional.Add(new Input(file.Name, await file.GetTextAsync()));
            var compilation = (await project.GetCompilationAsync())!;
            Require(!compilation.GetDiagnostics().Any(d => d.Severity == DiagnosticSeverity.Error), "fixture compiles");
            var diagnostics = await compilation.WithAnalyzers(ImmutableArray.Create<DiagnosticAnalyzer>(analyzer), new AnalyzerOptions(additional.ToImmutableArray())).GetAnalyzerDiagnosticsAsync();
            Require(!diagnostics.Any(d => d.Id == "AD0001"), "analyzer exception rejected");
            var missing = diagnostics.FirstOrDefault(d => d.Id == "RS0016");
            if (missing == null)
            {
                Require(!diagnostics.Any(d => d.Severity == DiagnosticSeverity.Error || d.Severity == DiagnosticSeverity.Warning), "fixed public API has no diagnostic warnings");
                break;
            }
            var actions = new List<CodeAction>();
            var document = project.GetDocument(original.Id)!;
            await fixer.RegisterCodeFixesAsync(new CodeFixContext(document, missing, (a, _) => actions.Add(a), CancellationToken.None));
            Require(actions.Count > 0, "actual source code fix registered");
            var operation = (await actions[0].GetOperationsAsync(CancellationToken.None)).OfType<ApplyChangesOperation>().Single();
            project = operation.ChangedSolution.GetProject(project.Id)!;
            applied++;
        }
        string baseline = (await project.AdditionalDocuments.Single(d => d.Name == "PublicAPI.Unshipped.txt").GetTextAsync()).ToString();
        Require(applied == 2 && baseline.Contains("Fixture\n") && baseline.Contains("static Fixture.Echo(string! value) -> string!"), "both source fixes generated exact nullable public API entries");
        Require((await project.GetDocument(original.Id)!.GetTextAsync()).ToString() == (await original.GetTextAsync()).ToString(), "API fix preserves source code");
        await Scenario("annotate", "#nullable enable\nFixture\n~static Fixture.Echo(string value) -> string\n", new AnnotatePublicApiFix(), "RS0036", false);
        await Scenario("enable-nullable", "Fixture\nstatic Fixture.Echo(string value) -> string\n", new NullableEnablePublicApiFix(), "RS0037", false);
        await Scenario("declare-fixall", "#nullable enable\n", new DeclarePublicApiFix(), "RS0016", true);
        await Scenario("annotate-fixall", "#nullable enable\nFixture\n~static Fixture.Echo(string value) -> string\n", new AnnotatePublicApiFix(), "RS0036", true);
        await Scenario("enable-nullable-fixall", "Fixture\nstatic Fixture.Echo(string value) -> string\n", new NullableEnablePublicApiFix(), "RS0037", true);

        async Task Scenario(string label, string shipped, CodeFixProvider provider, string expectedId, bool fixAll)
        {
            var fixture = workspace.AddProject(label, LanguageNames.CSharp)
                .WithCompilationOptions(new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary, nullableContextOptions: NullableContextOptions.Enable))
                .AddMetadataReferences(Directory.GetFiles(args[0], "*.dll").Select(p => MetadataReference.CreateFromFile(p)));
            var sourceDocument = fixture.AddDocument("Fixture.cs", await original.GetTextAsync());
            fixture = sourceDocument.Project.AddAdditionalDocument("PublicAPI.Shipped.txt", SourceText.From(shipped), filePath: Path.Combine(args[1], label, "PublicAPI.Shipped.txt")).Project;
            fixture = fixture.AddAdditionalDocument("PublicAPI.Unshipped.txt", SourceText.From(expectedId == "RS0037" ? "" : "#nullable enable\n"), filePath: Path.Combine(args[1], label, "PublicAPI.Unshipped.txt")).Project;
            var initial = await Analyze(fixture);
            var diagnostic = initial.FirstOrDefault(d => d.Id == expectedId);
            Require(diagnostic != null, label + " initial diagnostic " + string.Join(",", initial.Select(d => d.Id)));
            var document = fixture.GetDocument(sourceDocument.Id)!;
            var actions = new List<CodeAction>();
            await provider.RegisterCodeFixesAsync(new CodeFixContext(document, diagnostic!, (a, _) => actions.Add(a), CancellationToken.None));
            Require(actions.Count > 0, label + " action registered");
            CodeAction action = actions[0];
            if (fixAll)
            {
                var context = new FixAllContext(document, provider, FixAllScope.Document, action.EquivalenceKey, provider.FixableDiagnosticIds, new Diagnostics(initial), CancellationToken.None);
                action = (await provider.GetFixAllProvider()!.GetFixAsync(context))!;
                Require(action != null, label + " fix-all action registered");
            }
            var operation = (await action!.GetOperationsAsync(CancellationToken.None)).OfType<ApplyChangesOperation>().Single();
            fixture = operation.ChangedSolution.GetProject(fixture.Id)!;
            var remaining = await Analyze(fixture);
            Require(!remaining.Any(d => d.Id == expectedId || d.Id == "AD0001"), label + " target diagnostic cleared");
            Require((await fixture.GetDocument(sourceDocument.Id)!.GetTextAsync()).ToString() == (await original.GetTextAsync()).ToString(), label + " source unchanged");
            if (expectedId == "RS0037")
                Require((await fixture.AdditionalDocuments.Single(d=>d.Name=="PublicAPI.Shipped.txt").GetTextAsync()).ToString().StartsWith("#nullable enable"), label + " nullable directive added");
            else
                Require(!remaining.Any(d => d.Severity is DiagnosticSeverity.Warning or DiagnosticSeverity.Error), label + " diagnostics clean");
            Console.WriteLine("PASS " + label + " actual action, baseline update and source preservation");
        }
        async Task<ImmutableArray<Diagnostic>> Analyze(Project fixture)
        {
            var extra = new List<AdditionalText>();
            foreach (var file in fixture.AdditionalDocuments) extra.Add(new Input(file.Name, await file.GetTextAsync()));
            var compilation = (await fixture.GetCompilationAsync())!;
            Require(!compilation.GetDiagnostics().Any(d=>d.Severity==DiagnosticSeverity.Error), "fixture compilation");
            var diagnostics = await compilation.WithAnalyzers(ImmutableArray.Create<DiagnosticAnalyzer>(analyzer), new AnalyzerOptions(extra.ToImmutableArray())).GetAnalyzerDiagnosticsAsync();
            Require(!diagnostics.Any(d=>d.Id=="AD0001"), "analyzer exception rejected");
            return diagnostics;
        }
        Console.WriteLine("PASS source NS2 analyzer/codefix identities, Roslyn4.4 workspace, two actual public-API fixes, exact nullable baseline and diagnostic cleanup");
    }
    sealed class Diagnostics : FixAllContext.DiagnosticProvider
    {
        readonly ImmutableArray<Diagnostic> diagnostics;
        public Diagnostics(ImmutableArray<Diagnostic> values) { diagnostics = values; }
        public override Task<IEnumerable<Diagnostic>> GetDocumentDiagnosticsAsync(Document document, CancellationToken cancellationToken)
            => Task.FromResult<IEnumerable<Diagnostic>>(diagnostics.Where(d=>d.Location.IsInSource));
        public override Task<IEnumerable<Diagnostic>> GetProjectDiagnosticsAsync(Project project, CancellationToken cancellationToken)
            => Task.FromResult<IEnumerable<Diagnostic>>(diagnostics.Where(d=>!d.Location.IsInSource));
        public override Task<IEnumerable<Diagnostic>> GetAllDiagnosticsAsync(Project project, CancellationToken cancellationToken)
            => Task.FromResult<IEnumerable<Diagnostic>>(diagnostics);
    }
    sealed class Input : AdditionalText
    {
        readonly string path;
        readonly SourceText text;
        internal Input(string path, SourceText text) { this.path = path; this.text = text; }
        public override string Path => path;
        public override SourceText GetText(CancellationToken cancellationToken = default) => text;
    }
}
