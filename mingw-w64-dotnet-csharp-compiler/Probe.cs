using System;
using System.Collections.Immutable;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Diagnostics;
[Generator]
public sealed class ProbeGenerator:IIncrementalGenerator
{
 public void Initialize(IncrementalGeneratorInitializationContext context)
 {
  context.RegisterPostInitializationOutput(c=>c.AddSource("Generated.cs","internal static class GeneratedNumber { public const int Value = 42; public const string Compiler = \""+typeof(Compilation).Assembly.GetName().Version+"\"; }"));
 }
}
[DiagnosticAnalyzer(LanguageNames.CSharp)]
public sealed class ProbeAnalyzer:DiagnosticAnalyzer
{
 static readonly DiagnosticDescriptor Rule=new("CSC4901","Owned compiler analyzer","Forbidden class rejected by source compiler","Build",DiagnosticSeverity.Error,true);
 public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics=>ImmutableArray.Create(Rule);
 public override void Initialize(AnalysisContext context)
 {
  context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None);context.EnableConcurrentExecution();
  context.RegisterSyntaxNodeAction(c=>{var node=(ClassDeclarationSyntax)c.Node;if(node.Identifier.ValueText=="Forbidden")c.ReportDiagnostic(Diagnostic.Create(Rule,node.Identifier.GetLocation()));},SyntaxKind.ClassDeclaration);
 }
}
