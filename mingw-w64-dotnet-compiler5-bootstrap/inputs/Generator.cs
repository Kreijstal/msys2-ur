using System;
using System.Collections.Immutable;
using System.Reflection.Metadata;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Diagnostics;

[Generator]
public sealed class OwnedGenerator : IIncrementalGenerator
{
    public void Initialize(IncrementalGeneratorInitializationContext context)
    {
        context.RegisterPostInitializationOutput(output => {
            if (typeof(ImmutableArray<>).Assembly.GetName().Version!.Major != 9 ||
                typeof(MetadataReader).Assembly.GetName().Version!.Major != 9)
                throw new Exception("Compiler generator host must load exact source runtime9 dependencies");
            output.AddSource("GeneratedNumber.g.cs", "public static class GeneratedNumber { public const int Value=42; }");
        });
    }
}

[DiagnosticAnalyzer(LanguageNames.CSharp)]
public sealed class OwnedAnalyzer : DiagnosticAnalyzer
{
    static readonly DiagnosticDescriptor Rule = new("C5PKG001", "Compiler callback", "Original source compiler analyzer callback", "Source package", DiagnosticSeverity.Warning, true);
    public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics => ImmutableArray.Create(Rule);
    public override void Initialize(AnalysisContext context)
    {
        context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None);
        context.EnableConcurrentExecution();
        context.RegisterSyntaxNodeAction(c => {
            if (((ClassDeclarationSyntax)c.Node).Identifier.ValueText == "Probe")
                c.ReportDiagnostic(Diagnostic.Create(Rule, c.Node.GetLocation()));
        }, SyntaxKind.ClassDeclaration);
    }
}
