// Extract literal upstream C#/VB cases without executing upstream test code.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
class Program
{
 static void Main(string[] args)
 {
  var fixtures=new List<object>();var skipped=new List<string>();
  foreach(string file in Directory.GetFiles(args[0],"*Tests.cs",SearchOption.AllDirectories).OrderBy(x=>x))
  {
   var root=CSharpSyntaxTree.ParseText(File.ReadAllText(file)).GetRoot();
   var aliases=new Dictionary<string,(string analyzer,string fix,string language)>();
   foreach(var u in root.DescendantNodes().OfType<UsingDirectiveSyntax>().Where(u=>u.Alias!=null))
   {
    var g=u.Name.DescendantNodesAndSelf().OfType<GenericNameSyntax>().FirstOrDefault();
    if(g==null||!g.Identifier.ValueText.EndsWith("CodeFixVerifier")||g.TypeArgumentList.Arguments.Count!=2)continue;
    aliases[u.Alias.Name.Identifier.ValueText]=(g.TypeArgumentList.Arguments[0].ToString(),g.TypeArgumentList.Arguments[1].ToString(),g.Identifier.ValueText.StartsWith("VisualBasic")?"Visual Basic":"C#");
   }
   foreach(var method in root.DescendantNodes().OfType<MethodDeclarationSyntax>())
   {
    var attrs=method.AttributeLists.SelectMany(x=>x.Attributes).ToArray();
    if(!attrs.Any(a=>a.Name.ToString() is "Fact" or "Theory"))continue;
    string label=Path.GetRelativePath(args[0],file).Replace('\\','/')+"/"+method.Identifier.ValueText;
    if(attrs.Any(a=>a.ArgumentList?.Arguments.Any(x=>x.NameEquals?.Name.Identifier.ValueText=="Skip")==true)){skipped.Add(label+": upstream skip");continue;}
    if(method.DescendantNodes().Any(n=>n is IfStatementSyntax or ForEachStatementSyntax or ForStatementSyntax or WhileStatementSyntax)){skipped.Add(label+": control flow requires original harness");continue;}
    var inline=attrs.Where(a=>a.Name.ToString()=="InlineData").ToArray();
    if(method.ParameterList.Parameters.Count>0&&inline.Length==0){skipped.Add(label+": non-inline data source");continue;}
    for(int variant=0;variant<Math.Max(1,inline.Length);variant++)
    {
     string current=label+(inline.Length==0?"":"#"+variant);var values=new Dictionary<string,object>();var expressions=new Dictionary<string,ExpressionSyntax>();
     bool Eval(ExpressionSyntax e,out object value)
     {
      value=null;if(e==null)return false;
      if(e is LiteralExpressionSyntax literal){value=literal.Token.Value;return true;}
      if(e is IdentifierNameSyntax id)return values.TryGetValue(id.Identifier.ValueText,out value);
      if(e is ParenthesizedExpressionSyntax par)return Eval(par.Expression,out value);
      if(e.ToString() is "Environment.NewLine" or "System.Environment.NewLine"){value="\r\n";return true;}
      if(e.ToString() is "string.Empty" or "String.Empty"){value="";return true;}
      if(e is BinaryExpressionSyntax binary&&Eval(binary.Left,out var left)&&Eval(binary.Right,out var right))
      {
       if(binary.IsKind(SyntaxKind.AddExpression)){value=Convert.ToString(left)+Convert.ToString(right);return true;}
       if(binary.IsKind(SyntaxKind.EqualsExpression)){value=Equals(left,right);return true;}
       if(binary.IsKind(SyntaxKind.NotEqualsExpression)){value=!Equals(left,right);return true;}
      }
      if(e is ConditionalExpressionSyntax conditional&&Eval(conditional.Condition,out var choice)&&choice is bool b)return Eval(b?conditional.WhenTrue:conditional.WhenFalse,out value);
      if(e is SwitchExpressionSyntax sw&&Eval(sw.GoverningExpression,out var governing))
       foreach(var arm in sw.Arms)
       {
        if(arm.Pattern is DiscardPatternSyntax)return Eval(arm.Expression,out value);
        if(arm.Pattern is ConstantPatternSyntax cp&&Eval(cp.Expression,out var constant)&&Equals(governing,constant))return Eval(arm.Expression,out value);
       }
      if(e is InterpolatedStringExpressionSyntax interpolation)
      {
       var result=new StringBuilder();
       foreach(var part in interpolation.Contents)
        if(part is InterpolatedStringTextSyntax text)result.Append(text.TextToken.ValueText.Replace("{{","{").Replace("}}","}"));
        else if(part is InterpolationSyntax ins&&ins.FormatClause==null&&ins.AlignmentClause==null&&Eval(ins.Expression,out var v))result.Append(v);
        else return false;
       value=result.ToString();return true;
      }
      if(e is InvocationExpressionSyntax call&&call.Expression is MemberAccessExpressionSyntax member&&Eval(member.Expression,out var instance)&&instance is string s&&member.Name.Identifier.ValueText=="Replace"&&call.ArgumentList.Arguments.Count==2&&Eval(call.ArgumentList.Arguments[0].Expression,out var before)&&Eval(call.ArgumentList.Arguments[1].Expression,out var after))
      {value=s.Replace(Convert.ToString(before),Convert.ToString(after));return true;}
      return false;
     }
     void Variables(IEnumerable<VariableDeclaratorSyntax> variables)
     {foreach(var v in variables){if(v.Initializer!=null)expressions[v.Identifier.ValueText]=v.Initializer.Value;if(Eval(v.Initializer?.Value,out var result))values[v.Identifier.ValueText]=result;}}
     if(inline.Length!=0)
      for(int i=0;i<method.ParameterList.Parameters.Count;i++)
       if(i<inline[variant].ArgumentList.Arguments.Count&&Eval(inline[variant].ArgumentList.Arguments[i].Expression,out var value))values[method.ParameterList.Parameters[i].Identifier.ValueText]=value;
     Variables(root.DescendantNodes().OfType<FieldDeclarationSyntax>().SelectMany(f=>f.Declaration.Variables));
     Variables(method.DescendantNodes().OfType<VariableDeclaratorSyntax>());
     int? DiagnosticCount(ExpressionSyntax expression,int depth=0)
     {
      if(expression==null||depth>10)return null;
      if(expression is IdentifierNameSyntax id&&expressions.TryGetValue(id.Identifier.ValueText,out var original))return DiagnosticCount(original,depth+1);
      if(expression.ToString()=="DiagnosticResult.EmptyDiagnosticResults")return 0;
      if(expression is InitializerExpressionSyntax initializer)
      {
       int total=0;foreach(var e in initializer.Expressions){var count=DiagnosticCount(e,depth+1);if(count==null)return null;total+=count.Value;}return total;
      }
      if(expression is ImplicitArrayCreationExpressionSyntax array)return DiagnosticCount(array.Initializer,depth+1);
      if(expression.DescendantNodesAndSelf().OfType<InvocationExpressionSyntax>().Any(c=>c.Expression is MemberAccessExpressionSyntax m&&m.Name.Identifier.ValueText=="Diagnostic"))return 1;
      return null;
     }
     var creations=method.DescendantNodes().OfType<ObjectCreationExpressionSyntax>().Where(o=>o.Type is QualifiedNameSyntax q&&q.Left is IdentifierNameSyntax alias&&aliases.ContainsKey(alias.Identifier.ValueText)&&q.Right.Identifier.ValueText=="Test").ToArray();
     if(creations.Length!=0)
     {
      int number=0;
      foreach(var creation in creations)
      {
       var q=(QualifiedNameSyntax)creation.Type;var identity=aliases[((IdentifierNameSyntax)q.Left).Identifier.ValueText];
       string caseLabel=current+"@"+(number++);string configuredSource=null,configuredExpected=null;var additional=new List<string>();var additionalExpected=new List<string>();int? expectedCount=null;int actionIndex=0;string unsupported=null;
       void ReadState(InitializerExpressionSyntax state,bool fixedState)
       {
        foreach(var entry in state.Expressions)
        {
         if(entry is not AssignmentExpressionSyntax assignment){unsupported="state entry";continue;}
         string name=assignment.Left.ToString();
         if(name=="Sources"&&assignment.Right is InitializerExpressionSyntax list)
         {
          var strings=new List<string>();foreach(var value in list.Expressions){if(Eval(value,out var result)&&result is string text)strings.Add(text);else unsupported="nonliteral configuredSource list";}
          if(strings.Count>0)
          {
           if(fixedState){configuredExpected=strings[0];additionalExpected.AddRange(strings.Skip(1));}
           else{configuredSource=strings[0];additional.AddRange(strings.Skip(1));}
          }
         }
         else if(name=="ExpectedDiagnostics"&&!fixedState){expectedCount=DiagnosticCount(assignment.Right);if(expectedCount==null)unsupported="nonliteral diagnostic list";}
         else unsupported="state property "+name;
        }
       }
       if(creation.Initializer==null){skipped.Add(caseLabel+": no literal test initializer");continue;}
       foreach(var entry in creation.Initializer.Expressions)
       {
        if(entry is not AssignmentExpressionSyntax assignment){unsupported="test entry";continue;}
        string name=assignment.Left.ToString();
        if(name is "TestCode" or "FixedCode")
        {
         if(Eval(assignment.Right,out var value)&&value is string text){if(name=="TestCode")configuredSource=text;else configuredExpected=text;}else unsupported="nonliteral "+name;
        }
        else if(name is "TestState" or "FixedState"&&assignment.Right is InitializerExpressionSyntax state)ReadState(state,name=="FixedState");
        else if(name=="CodeActionIndex")
        {if(Eval(assignment.Right,out var index)&&index is int n)actionIndex=n;else unsupported="nonliteral action index";}
        else if(name=="CodeActionEquivalenceKey"){} // Exact resulting configuredSource is checked; key assertion remains outside this adapter.
        else if(name=="CompilerDiagnostics"){} // Original compiler assertions are outside this .NET8 adapter.
        else unsupported="test property "+name;
       }
       if(unsupported!=null||configuredSource==null){skipped.Add(caseLabel+": "+(unsupported??"missing literal configuredSource"));continue;}
       if(additionalExpected.Count!=0&&!additionalExpected.SequenceEqual(additional)){skipped.Add(caseLabel+": additional-document edits require structural adapter");continue;}
       fixtures.Add(new{label=caseLabel,identity.analyzer,identity.fix,identity.language,source=configuredSource,expected=configuredExpected,additional_sources=additional,expected_count=expectedCount,check_spans=expectedCount==null,action_index=actionIndex});
      }
      // Do not execute direct helper calls from methods whose configured Test objects are handled above.
      continue;
     }
     var calls=method.DescendantNodes().OfType<InvocationExpressionSyntax>().Where(c=>c.Expression is MemberAccessExpressionSyntax m&&m.Expression is IdentifierNameSyntax id&&aliases.ContainsKey(id.Identifier.ValueText)&&m.Name.Identifier.ValueText is "VerifyAnalyzerAsync" or "VerifyCodeFixAsync").ToArray();
     if(calls.Length!=1){skipped.Add(current+": configured/new Test or multiple/helper verification calls require original harness");continue;}
     var call=calls[0];var access=(MemberAccessExpressionSyntax)call.Expression;var alias=aliases[((IdentifierNameSyntax)access.Expression).Identifier.ValueText];bool fix=access.Name.Identifier.ValueText=="VerifyCodeFixAsync";
     var a=call.ArgumentList.Arguments;
     if(a.Count!=(fix?2:1)){skipped.Add(current+": explicit expected diagnostics/options require configured adapter");continue;}
     if(!Eval(a[0].Expression,out var input)||input is not string source){skipped.Add(current+": source expression unsupported");continue;}
     string expected=null;
     object output=null;
     if(fix&&(!Eval(a[1].Expression,out output)||output is not string)){skipped.Add(current+": fixed source expression unsupported");continue;}
     if(fix)expected=(string)output;
     fixtures.Add(new{label=current,alias.analyzer,alias.fix,alias.language,source,expected});
    }
   }
  }
  using var expectedAssemblies=JsonDocument.Parse(File.ReadAllText(args[1]));
  var allowed=expectedAssemblies.RootElement.EnumerateObject().SelectMany(a=>a.Value.GetProperty("inventory").GetProperty("analyzers").EnumerateArray().Select(v=>v.GetString())).ToHashSet();
  var selected=new List<object>();var perAnalyzer=new Dictionary<string,int>();
  foreach(var item in fixtures)
  {
   using var doc=JsonDocument.Parse(JsonSerializer.Serialize(item));var entry=doc.RootElement;
   string analyzer=entry.GetProperty("analyzer").GetString();
   if(!allowed.Contains(analyzer)){skipped.Add(entry.GetProperty("label").GetString()+": analyzer outside shipping package");continue;}
   if(entry.TryGetProperty("additional_sources",out var additional)&&additional.GetArrayLength()!=0){skipped.Add(entry.GetProperty("label").GetString()+": selected adapter is single-document");continue;}
   string key=analyzer+"|"+entry.GetProperty("language").GetString();perAnalyzer.TryGetValue(key,out int count);
   if(count>=6)continue;
   perAnalyzer[key]=count+1;selected.Add(item);
  }
  foreach(bool vb in new[]{false,true})
   foreach(string method in new[]{"StartsWith","EndsWith","IndexOf","LastIndexOf"})
    foreach(bool named in new[]{false,true})
    {
     bool index=method.Contains("IndexOf");string argsBefore=index?(named?(vb?"\"a\", startIndex:=0, count:=1, comparisonType:=StringComparison.Ordinal":"\"a\", startIndex: 0, count: 1, comparisonType: StringComparison.Ordinal"):"\"a\", 0, 1, StringComparison.Ordinal"):"\"a\", StringComparison.Ordinal";
     string argsAfter=vb?"\"a\"c":"'a'";
     if(index)argsAfter+=named?(vb?", startIndex:=0, count:=1":", startIndex: 0, count: 1"):", 0, 1";
     string before=vb?$"Imports System\nPublic Class C\n    Public Function M(value As String) As {(index?"Integer":"Boolean")}\n        Return value.{method}[|({argsBefore})|]\n    End Function\nEnd Class":$"using System;\npublic class C\n{{\n    public {(index?"int":"bool")} M(string value)\n    {{\n        return value.{method}[|({argsBefore})|];\n    }}\n}}";
     string after=before.Replace("[|("+argsBefore+")|]","("+argsAfter+")");
     selected.Add(new{label="owned:CharOverload:"+(vb?"VB":"CS")+":"+method+":"+(named?"Named":"Positional"),analyzer=vb?"Microsoft.NetCore.VisualBasic.Analyzers.Performance.BasicUseStringMethodCharOverloadWithSingleCharacters":"Microsoft.CodeAnalysis.CSharp.NetAnalyzers.Microsoft.NetCore.Analyzers.Performance.CSharpUseStringMethodCharOverloadWithSingleCharacters",fix=vb?"Microsoft.NetCore.VisualBasic.Analyzers.Performance.BasicUseStringMethodCharOverloadWithSingleCharactersFixer":"Microsoft.NetCore.CSharp.Analyzers.Performance.CSharpUseStringMethodCharOverloadWithSingleCharactersFixer",language=vb?"Visual Basic":"C#",source=before,expected=after});
    }
  fixtures=selected;
  Console.WriteLine(JsonSerializer.Serialize(new{fixtures,skipped},new JsonSerializerOptions{WriteIndented=true}));
 }
}
