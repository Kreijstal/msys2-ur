using System.Collections.Immutable;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.Diagnostics;
using Microsoft.CodeAnalysis.Text;
using Microsoft.CodeAnalysis.VisualBasic;
using Microsoft.CodeAnalysis.VisualBasic.Syntax;

[DiagnosticAnalyzer(LanguageNames.VisualBasic)]
public sealed class OwnedAnalyzer : DiagnosticAnalyzer
{
 static readonly DiagnosticDescriptor Rule=new("VBC4901","Owned forbidden class","Owned forbidden class","Compiler host check",DiagnosticSeverity.Error,true);
 public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics=>ImmutableArray.Create(Rule);
 public override void Initialize(AnalysisContext context)
 {
  context.EnableConcurrentExecution();context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None);
  context.RegisterSyntaxNodeAction(c=>{var node=(ClassStatementSyntax)c.Node;if(node.Identifier.ValueText=="Forbidden")c.ReportDiagnostic(Diagnostic.Create(Rule,node.Identifier.GetLocation()));},SyntaxKind.ClassStatement);
 }
}
[Generator(LanguageNames.VisualBasic)]
public sealed class OwnedGenerator : IIncrementalGenerator
{
 public void Initialize(IncrementalGeneratorInitializationContext context)
 {
  context.RegisterPostInitializationOutput(c=>c.AddSource("GeneratedNumber.g.vb",SourceText.From("Friend Module GeneratedNumber\n Friend Const Value As Integer = 42\n Friend Const Compiler As String = \""+typeof(Compilation).Assembly.GetName().Version+"\"\nEnd Module\n",System.Text.Encoding.UTF8)));
 }
}
