using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
class Program
{
 static void Main(string[] args)
 {
  var fixtures=new List<object>();var skipped=new List<string>();
  foreach(string file in Directory.GetFiles(args[0],"*UnitTests.cs",SearchOption.AllDirectories).OrderBy(p=>p))
  {
   var root=CSharpSyntaxTree.ParseText(File.ReadAllText(file)).GetRoot();
   var generic=root.DescendantNodes().OfType<GenericNameSyntax>().FirstOrDefault(g=>g.Identifier.ValueText=="CSharpCodeFixVerifier"||g.Identifier.ValueText=="CSharpCodeFixTest");
   if(generic==null)continue;
   string analyzer=generic.TypeArgumentList.Arguments[0].ToString(),fix=generic.TypeArgumentList.Arguments[1].ToString();
   foreach(var method in root.DescendantNodes().OfType<MethodDeclarationSyntax>())
   {
    var attributes=method.AttributeLists.SelectMany(a=>a.Attributes).ToArray();
    if(!attributes.Any(a=>a.Name.ToString() is "Fact" or "Theory"))continue;
    string label=Path.GetRelativePath(args[0],file).Replace('\\','/')+"/"+method.Identifier.ValueText;
    if(attributes.Any(a=>a.ArgumentList?.Arguments.Any(x=>x.NameEquals?.Name.Identifier.ValueText=="Skip")==true)){skipped.Add(label+": upstream skip");continue;}
    var inline=attributes.Where(a=>a.Name.ToString()=="InlineData").ToArray();
    bool memberKeywords=attributes.Any(a=>a.Name.ToString()=="MemberData")&&root.ToString().Contains("SyntaxFacts.GetKeywordKinds()");
    var keywords=memberKeywords?SyntaxFacts.GetKeywordKinds().Select(SyntaxFacts.GetText).ToArray():Array.Empty<string>();
    int variants=inline.Length!=0?inline.Length:memberKeywords?keywords.Length:1;
    for(int variant=0;variant<variants;variant++)
    {
     var values=new Dictionary<string,string>();
     if(inline.Length!=0)
      for(int i=0;i<method.ParameterList.Parameters.Count;i++)
       if(inline[variant].ArgumentList.Arguments[i].Expression is LiteralExpressionSyntax literal)values[method.ParameterList.Parameters[i].Identifier.ValueText]=literal.Token.ValueText;
     if(memberKeywords)
     {
      if(string.IsNullOrEmpty(keywords[variant])){skipped.Add(label+"#"+variant+": current Roslyn keyword enum has no text spelling; covered by owned empty-langword negative");continue;}
      values[method.ParameterList.Parameters.Single().Identifier.ValueText]=keywords[variant];
     }
     string Eval(ExpressionSyntax e)
     {
      if(e is LiteralExpressionSyntax literal&&literal.IsKind(SyntaxKind.StringLiteralExpression))return literal.Token.ValueText;
      if(e is IdentifierNameSyntax id)return values.TryGetValue(id.Identifier.ValueText,out var value)?value:null;
      if(e is BinaryExpressionSyntax binary&&binary.IsKind(SyntaxKind.AddExpression))return Eval(binary.Left) is string left&&Eval(binary.Right) is string right?left+right:null;
      if(e is InterpolatedStringExpressionSyntax interpolation)
      {
       var result=new System.Text.StringBuilder();
       foreach(var content in interpolation.Contents)
       {
        if(content is InterpolatedStringTextSyntax text)result.Append(text.TextToken.ValueText.Replace("{{","{").Replace("}}","}"));
        else if(content is InterpolationSyntax part&&part.FormatClause==null&&part.AlignmentClause==null&&Eval(part.Expression) is string replacement)result.Append(replacement);
        else return null;
       }
       return result.ToString();
      }
      return null;
     }
     foreach(var variable in method.DescendantNodes().OfType<VariableDeclaratorSyntax>())
     {var value=variable.Initializer==null?null:Eval(variable.Initializer.Value);if(value!=null)values[variable.Identifier.ValueText]=value;}
     string caseLabel=label+(variants==1?"":"#"+variant);
     if(!values.TryGetValue("testCode",out string input)){skipped.Add(caseLabel+": nonliteral source");continue;}
     bool isFix=values.TryGetValue("fixedCode",out string output);
     var calls=method.DescendantNodes().OfType<InvocationExpressionSyntax>().Where(c=>c.Expression.ToString().EndsWith(isFix?"VerifyCodeFixAsync":"VerifyAnalyzerAsync")).ToArray();
     bool configured=calls.Length!=1||calls[0].ArgumentList.Arguments.Count!=(isFix?2:1);
     bool compilerWarnings=method.ToString().Contains("CompilerDiagnostics.Warnings");
     fixtures.Add(new{label=caseLabel,analyzer,fix,source=input,expected=isFix?output:null,configured,compilerWarnings});
    }
   }
  }
  fixtures.Add(new{label="owned:EmptyLangwordRejected",analyzer="DocumentationAnalyzers.PortabilityRules.DOC207UseSeeLangwordCorrectly",fix="Microsoft.CodeAnalysis.Testing.EmptyCodeFixProvider",source="/// <summary><see [|langword|]=\"\"/><see [|langword|]=\"\"></see></summary>\nclass TestClass {}\n",expected=(string)null,configured=false,compilerWarnings=false});
  Console.WriteLine(JsonSerializer.Serialize(new{fixtures,skipped},new JsonSerializerOptions{WriteIndented=true}));
 }
}
