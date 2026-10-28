// Select direct, literal, single-document upstream Fact vectors; never execute upstream test code.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using CS=Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.VisualBasic;
using VB=Microsoft.CodeAnalysis.VisualBasic.Syntax;
class Program
{
 static void Main(string[] args)
 {
  using var expected=JsonDocument.Parse(File.ReadAllText(args[1]));
  var analyzerNames=expected.RootElement.EnumerateObject().SelectMany(a=>a.Value.GetProperty("inventory").GetProperty("analyzers").EnumerateArray().Select(v=>v.GetString())).ToArray();
  var fixerNames=expected.RootElement.EnumerateObject().SelectMany(a=>a.Value.GetProperty("inventory").GetProperty("code_fixes").EnumerateArray().Select(v=>v.GetString())).ToArray();
  var features=new[]{"MakeFieldReadonly","SimplifyBooleanExpression","RemoveUnnecessaryCast","UseObjectInitializer","UseCollectionInitializer","UseCompoundAssignment","RemoveRedundantEquality","UseCoalesceExpression","UseNullPropagation","RemoveUnusedMembers","RemoveUnnecessaryImports","UseExplicitTupleName","UseSystemHashCode","ConvertTypeOfToNameOf"};
  var cases=new List<object>();var skipped=new SortedDictionary<string,string>();
  string Find(IEnumerable<string> types,string[] names)=>types.Select(t=>names.SingleOrDefault(n=>n.Split('.').Last()==t.Split('.').Last())).FirstOrDefault(n=>n!=null);
  foreach(string language in new[]{"CSharp","VisualBasic"})
  {
   var tests=Path.Combine(args[0],"src","Analyzers",language,"Tests");
   foreach(string file in Directory.GetFiles(tests,language=="CSharp"?"*.cs":"*.vb",SearchOption.AllDirectories).OrderBy(f=>f))
   {
    string relative=Path.GetRelativePath(args[0],file).Replace('\\','/');
    if(!features.Any(f=>relative.Split('/').Contains(f)))continue;
    bool vb=language=="VisualBasic";SyntaxNode root=vb?VisualBasicSyntaxTree.ParseText(File.ReadAllText(file)).GetRoot():CSharpSyntaxTree.ParseText(File.ReadAllText(file)).GetRoot();
    var providers=vb?root.DescendantNodes().OfType<VB.MethodBlockSyntax>().Where(m=>m.SubOrFunctionStatement.Identifier.ValueText=="CreateDiagnosticProviderAndFixer").Cast<SyntaxNode>().ToArray():root.DescendantNodes().OfType<CS.MethodDeclarationSyntax>().Where(m=>m.Identifier.ValueText=="CreateDiagnosticProviderAndFixer").Cast<SyntaxNode>().ToArray();
    var types=providers.SelectMany(m=>vb?m.DescendantNodes().OfType<VB.ObjectCreationExpressionSyntax>().Select(n=>n.Type.ToString()):m.DescendantNodes().OfType<CS.ObjectCreationExpressionSyntax>().Select(n=>n.Type.ToString())).ToArray();
    string analyzer=Find(types,analyzerNames),fixer=Find(types,fixerNames);
    if(analyzer==null||fixer==null){skipped[relative]="provider/fixer declared elsewhere or not in CodeStyle package";continue;}
    var methods=vb?root.DescendantNodes().OfType<VB.MethodBlockSyntax>().Cast<SyntaxNode>():root.DescendantNodes().OfType<CS.MethodDeclarationSyntax>().Cast<SyntaxNode>();
    int positive=0,negative=0;
    foreach(var method in methods)
    {
     bool fact=vb?((VB.MethodBlockSyntax)method).SubOrFunctionStatement.AttributeLists.SelectMany(a=>a.Attributes).Any(a=>a.Name.ToString() is "Fact" or "WpfFact"):((CS.MethodDeclarationSyntax)method).AttributeLists.SelectMany(a=>a.Attributes).Any(a=>a.Name.ToString() is "Fact" or "WpfFact");
     if(!fact)continue;
     string methodName=vb?((VB.MethodBlockSyntax)method).SubOrFunctionStatement.Identifier.ValueText:((CS.MethodDeclarationSyntax)method).Identifier.ValueText;
     var calls=method.DescendantNodes().Where(n=>vb?n is VB.InvocationExpressionSyntax:n is CS.InvocationExpressionSyntax).ToArray();
     var helpers=calls.Where(c=>(vb?((VB.InvocationExpressionSyntax)c).Expression.ToString():((CS.InvocationExpressionSyntax)c).Expression.ToString()) is "TestInRegularAndScriptAsync" or "TestInRegularAndScript1Async" or "TestMissingInRegularAndScriptAsync").ToArray();
     if(helpers.Length!=1){skipped[relative+"::"+methodName]="not one direct supported helper invocation";continue;}
     var call=helpers.Single();string helper=vb?((VB.InvocationExpressionSyntax)call).Expression.ToString():((CS.InvocationExpressionSyntax)call).Expression.ToString();
     bool missing=helper.StartsWith("TestMissing");
     var expressions=vb?((VB.InvocationExpressionSyntax)call).ArgumentList.Arguments.OfType<VB.SimpleArgumentSyntax>().Select(a=>(SyntaxNode)a.Expression).ToArray():((CS.InvocationExpressionSyntax)call).ArgumentList.Arguments.Select(a=>(SyntaxNode)a.Expression).ToArray();
     if(expressions.Length!=(missing?1:2)||expressions.Any(e=>vb?e is not VB.LiteralExpressionSyntax:e is not CS.LiteralExpressionSyntax)) {skipped[relative+"::"+methodName]="options/helper/generated/XML/nonliteral arguments require original harness";continue;}
     var strings=expressions.Select(e=>vb?((VB.LiteralExpressionSyntax)e).Token.ValueText:((CS.LiteralExpressionSyntax)e).Token.ValueText).ToArray();
     if(strings.Any(s=>s.Contains("{|"))){skipped[relative+"::"+methodName]="named/fix-all markup requires original harness";continue;}
     if(missing?negative>=4:positive>=8)continue;
     if(missing)negative++;else positive++;
     cases.Add(new{language=vb?LanguageNames.VisualBasic:LanguageNames.CSharp,file=relative,method=methodName,analyzer,fixer,source=strings[0],expected=missing?null:strings[1],missing});
    }
   }
  }
  Console.WriteLine(JsonSerializer.Serialize(new{cases,skipped,scope="Selected direct literal Fact vectors only: regular compilation, diagnostic/span presence or absence, first actual code action and exact fixed text. Not upstream script/compiler-diagnostic/key/iteration/multi-document/xUnit assertions."},new JsonSerializerOptions{WriteIndented=true}));
 }
}
