using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

class ExtractFixtures
{
 static void Main(string[] args)
 {
  var fixtures=new List<object>();var skipped=new List<string>();
  foreach(string file in Directory.GetFiles(args[0],"*UnitTests.cs",SearchOption.AllDirectories).OrderBy(p=>p))
  {
   if(!file.Replace('\\','/').Contains("/StyleCop.Analyzers.Test"))continue;
   var root=CSharpSyntaxTree.ParseText(File.ReadAllText(file)).GetRoot();
   if(root.DescendantNodes().OfType<UsingDirectiveSyntax>().Any(u=>u.Name.ToString()=="CombinedUsingDirectivesVerifier"))
   {skipped.Add(Path.GetRelativePath(args[0],file).Replace('\\','/')+": combined synthetic analyzer harness is not part of the single-analyzer fixture adapter");continue;}
   var generic=root.DescendantNodes().OfType<GenericNameSyntax>().FirstOrDefault(g=>g.Identifier.ValueText is "StyleCopCodeFixVerifier" or "StyleCopDiagnosticVerifier");
   if(generic==null)continue;
   string analyzer=generic.TypeArgumentList.Arguments[0].ToString(),fix=generic.TypeArgumentList.Arguments.Count>1?generic.TypeArgumentList.Arguments[1].ToString():null;
   foreach(var method in root.DescendantNodes().OfType<MethodDeclarationSyntax>())
   {
    var attributes=method.AttributeLists.SelectMany(a=>a.Attributes).ToArray();
    if(!attributes.Any(a=>a.Name.ToString() is "Fact" or "Theory"))continue;
    string label=Path.GetRelativePath(args[0],file).Replace('\\','/')+"/"+method.Identifier.ValueText;
    void Skip(string reason)=>skipped.Add(label+": "+reason);
    if(attributes.Any(a=>a.ArgumentList?.Arguments.Any(x=>x.NameEquals?.Name.Identifier.ValueText=="Skip")==true)){Skip("upstream skip");continue;}
    if(method.DescendantNodes().Any(n=>n is IfStatementSyntax or ForEachStatementSyntax or ForStatementSyntax or WhileStatementSyntax or SwitchStatementSyntax)){Skip("control flow requires original harness");continue;}
    var inline=attributes.Where(a=>a.Name.ToString()=="InlineData").ToArray();
    if(method.ParameterList.Parameters.Count>0&&inline.Length==0){Skip("non-inline data source");continue;}
    for(int variant=0;variant<Math.Max(1,inline.Length);variant++)
    {
     var values=new Dictionary<string,object>();var expressions=new Dictionary<string,ExpressionSyntax>();
     bool TryEval(ExpressionSyntax e,out object result)
     {
      result=null;if(e==null)return false;
      if(e is LiteralExpressionSyntax lit){result=lit.Token.Value;return true;}
      if(e is ParenthesizedExpressionSyntax par)return TryEval(par.Expression,out result);
      if(e is IdentifierNameSyntax id)return values.TryGetValue(id.Identifier.ValueText,out result);
      if(e.ToString() is "Environment.NewLine" or "System.Environment.NewLine"){result="\n";return true;}
      if(e.ToString() is "string.Empty" or "String.Empty"){result="";return true;}
      if(e is BinaryExpressionSyntax binary&&binary.IsKind(SyntaxKind.AddExpression)&&TryEval(binary.Left,out var left)&&TryEval(binary.Right,out var right)){result=Convert.ToString(left,System.Globalization.CultureInfo.InvariantCulture)+Convert.ToString(right,System.Globalization.CultureInfo.InvariantCulture);return true;}
      if(e is InterpolatedStringExpressionSyntax interpolation)
      {
       var text=new StringBuilder();
       foreach(var part in interpolation.Contents)
        if(part is InterpolatedStringTextSyntax literal)text.Append(literal.TextToken.ValueText.Replace("{{","{").Replace("}}","}"));
        else if(part is InterpolationSyntax ins&&ins.FormatClause==null&&ins.AlignmentClause==null&&TryEval(ins.Expression,out var value))text.Append(value);
        else return false;
       result=text.ToString();return true;
      }
      if(e is InvocationExpressionSyntax invocation&&invocation.Expression.ToString() is "string.Format" or "String.Format")
      {
       var a=invocation.ArgumentList.Arguments;var v=new List<object>();
       foreach(var x in a){if(!TryEval(x.Expression,out var item))return false;v.Add(item);}
       if(v.Count<1||v[0] is not string fmt)return false;
       result=string.Format(System.Globalization.CultureInfo.InvariantCulture,fmt,v.Skip(1).ToArray());return true;
      }
      if(e is InvocationExpressionSyntax call&&call.Expression is MemberAccessExpressionSyntax member&&TryEval(member.Expression,out var instance)&&instance is string input)
      {
       if(member.Name.Identifier.ValueText=="Replace"&&call.ArgumentList.Arguments.Count==2&&TryEval(call.ArgumentList.Arguments[0].Expression,out var old)&&TryEval(call.ArgumentList.Arguments[1].Expression,out var replacement)){result=input.Replace(Convert.ToString(old),Convert.ToString(replacement));return true;}
      }
      return false;
     }
     string StringValue(ExpressionSyntax e)=>TryEval(e,out var value)&&value is string s?s:null;
     int? Count(ExpressionSyntax e,int depth=0)
     {
      if(e==null||depth>10)return null;
      if(e is IdentifierNameSyntax id&&expressions.TryGetValue(id.Identifier.ValueText,out var initial))return Count(initial,depth+1);
      if(e.ToString()=="DiagnosticResult.EmptyDiagnosticResults"||e.ToString()=="Array.Empty<DiagnosticResult>()")return 0;
      if(e is ArrayCreationExpressionSyntax array&&array.Initializer!=null)return array.Initializer.Expressions.Count;
      if(e is ImplicitArrayCreationExpressionSyntax implicitArray)return implicitArray.Initializer.Expressions.Count;
      if(e is InitializerExpressionSyntax initializer)return initializer.Expressions.Count;
      if(e.DescendantNodesAndSelf().OfType<InvocationExpressionSyntax>().Any(c=>c.Expression.ToString() is "Diagnostic" or "DiagnosticResult.CompilerError" or "DiagnosticResult.CompilerWarning"))return 1;
      return null;
     }
     int CompilerCount(ExpressionSyntax e,int depth=0)
     {
      if(e==null||depth>10)return 0;
      if(e is IdentifierNameSyntax id&&expressions.TryGetValue(id.Identifier.ValueText,out var initial))return CompilerCount(initial,depth+1);
      return e.DescendantNodesAndSelf().OfType<InvocationExpressionSyntax>().Count(c=>c.Expression.ToString() is "DiagnosticResult.CompilerError" or "DiagnosticResult.CompilerWarning" || c.Expression.ToString()=="Diagnostic"&&c.ArgumentList.Arguments.FirstOrDefault()?.Expression is LiteralExpressionSyntax literal&&literal.Token.ValueText.StartsWith("CS"));
     }
     string[] CompilerIds(ExpressionSyntax e,int depth=0)
     {
      if(e==null||depth>10)return Array.Empty<string>();
      if(e is IdentifierNameSyntax id&&expressions.TryGetValue(id.Identifier.ValueText,out var initial))return CompilerIds(initial,depth+1);
      return e.DescendantNodesAndSelf().OfType<InvocationExpressionSyntax>().Where(c=>c.Expression.ToString() is "DiagnosticResult.CompilerError" or "DiagnosticResult.CompilerWarning" or "Diagnostic").SelectMany(c=>c.ArgumentList.Arguments.Take(1)).Select(a=>StringValue(a.Expression)).Where(s=>s?.StartsWith("CS")==true).Distinct().ToArray();
     }
     void Variables(IEnumerable<VariableDeclaratorSyntax> declarations)
     {
      foreach(var variable in declarations)
      {
       if(variable.Initializer==null)continue;
       expressions[variable.Identifier.ValueText]=variable.Initializer.Value;
       if(TryEval(variable.Initializer.Value,out var value))values[variable.Identifier.ValueText]=value;
      }
     }
     if(inline.Length>0)
      for(int i=0;i<method.ParameterList.Parameters.Count;i++)
       if(i<inline[variant].ArgumentList.Arguments.Count&&TryEval(inline[variant].ArgumentList.Arguments[i].Expression,out var v))values[method.ParameterList.Parameters[i].Identifier.ValueText]=v;
     Variables(root.DescendantNodes().OfType<FieldDeclarationSyntax>().SelectMany(f=>f.Declaration.Variables));
     var helpers=root.DescendantNodes().OfType<MethodDeclarationSyntax>().Where(m=>!m.AttributeLists.SelectMany(a=>a.Attributes).Any(a=>a.Name.ToString() is "Fact" or "Theory")).ToArray();
     foreach(var helper in helpers)Variables(helper.DescendantNodes().OfType<VariableDeclaratorSyntax>());
     Variables(method.DescendantNodes().OfType<VariableDeclaratorSyntax>());
     string defaultSettings=null;bool unknownHelperSettings=false;
     bool defaultUseTabs=false;int defaultTabSize=4,defaultIndentationSize=4;
     var xmlReferences=new Dictionary<string,string>();
     foreach(var helper in helpers)
     {
      foreach(var assignment in helper.DescendantNodes().OfType<AssignmentExpressionSyntax>())
      {
       string property=assignment.Left.ToString();
       if(property=="Settings")
       {
        bool parameter=helper.ParameterList.Parameters.Any(p=>p.Identifier.ValueText==assignment.Right.ToString());
        string value=parameter?null:StringValue(assignment.Right);
        if(value!=null)defaultSettings=value;
        else if(values.TryGetValue("TestSettings",out var testSettings)&&testSettings is string s&&helpers.Any(m=>m.DescendantNodes().OfType<ArgumentSyntax>().Any(a=>a.Expression.ToString()=="TestSettings")))defaultSettings=s;
        else if(!parameter)unknownHelperSettings=true;
       }
       if(property=="UseTabs"&&TryEval(assignment.Right,out var tabs)&&tabs is bool b)defaultUseTabs=b;
       if(property=="TabSize"&&TryEval(assignment.Right,out var size)&&size is int n)defaultTabSize=n;
       if(property=="IndentationSize"&&TryEval(assignment.Right,out var indent)&&indent is int i)defaultIndentationSize=i;
       if(property=="XmlReferences"&&assignment.Right is InitializerExpressionSyntax references)
        foreach(var element in references.Expressions.OfType<InitializerExpressionSyntax>())
         if(element.Expressions.Count==2&&StringValue(element.Expressions[0]) is string name&&StringValue(element.Expressions[1]) is string xml)xmlReferences[name]=xml;
      }
     }
     string caseLabel=label+(inline.Length==0?"":"#"+variant);int added=0;
     string language="CSharp12"; // Upstream's default parse version is null: the current compiler default.
     int assignmentsThrough=0;
     foreach(var call in method.DescendantNodes().OfType<InvocationExpressionSyntax>())
     {
      string name=call.Expression is IdentifierNameSyntax i?i.Identifier.ValueText:call.Expression is MemberAccessExpressionSyntax m?m.Name.Identifier.ValueText:"";
      bool isFix=name=="VerifyCSharpFixAsync";if(!isFix&&name!="VerifyCSharpDiagnosticAsync")continue;
      foreach(var assignment in method.DescendantNodes().OfType<AssignmentExpressionSyntax>().Where(a=>a.Parent is ExpressionStatementSyntax&&a.Left is IdentifierNameSyntax&&a.SpanStart>assignmentsThrough&&a.SpanStart<call.SpanStart).OrderBy(a=>a.SpanStart))
      {
       string variable=((IdentifierNameSyntax)assignment.Left).Identifier.ValueText;
       if(TryEval(assignment.Right,out var value))values[variable]=value;
       expressions[variable]=assignment.Right;
      }
      assignmentsThrough=call.SpanStart;
      var a=call.ArgumentList.Arguments.Select(x=>x.Expression).ToArray();int start=0;
      if(a.Length<3)continue;
      if(StringValue(a[0])==null){if(!a[0].ToString().StartsWith("LanguageVersion."))continue;language=a[0].ToString().Contains(".OrLaterDefault()")?"CSharp12":a[0].ToString().Split('.').Last();start++;}
      int normal=isFix?4:3;int extra=a.Length-start-normal;if(extra is not (0 or 1))continue;
      string input=StringValue(a[start]);string settings=extra==1?StringValue(a[start+1]):defaultSettings;
      if(extra==0&&unknownHelperSettings){skipped.Add(caseLabel+": dynamic helper settings require original harness");continue;}
      if(extra==1&&settings==null&&!a[start+1].IsKind(SyntaxKind.NullLiteralExpression))continue;
      int diagIndex=start+1+extra;int? count=Count(a[diagIndex]);
      string expected=isFix?StringValue(a[diagIndex+1]):null;
      if(input==null||count==null||(isFix&&expected==null))continue;
      fixtures.Add(new{label=caseLabel+"/call"+added++,analyzer,fix,source=input,expected,settings,diagnostics=count.Value,compilerDiagnostics=CompilerCount(a[diagIndex]),compilerIds=CompilerIds(a[diagIndex]),xmlReferences,language,actionIndex=0,useTabs=defaultUseTabs,tabSize=defaultTabSize,indentationSize=defaultIndentationSize});
     }
     // Preserve simple object-initializer tests, including explicit settings.
     foreach(var creation in method.DescendantNodes().OfType<ObjectCreationExpressionSyntax>().Where(c=>c.Type.ToString()=="CSharpTest"&&c.Initializer!=null))
     {
      var fields=creation.Initializer.Expressions.OfType<AssignmentExpressionSyntax>().ToDictionary(a=>a.Left.ToString(),a=>a.Right);
      var allowed=new[]{"TestCode","FixedCode","Settings","ExpectedDiagnostics","CodeActionIndex","BatchFixedCode","NumberOfFixAllIterations","NumberOfIncrementalIterations"};
      if(fields.Keys.Any(k=>!allowed.Contains(k))||!fields.TryGetValue("TestCode",out var sourceExpression))continue;
      string input=StringValue(sourceExpression),expected=fields.TryGetValue("FixedCode",out var fixedExpression)?StringValue(fixedExpression):null;
      string settings=fields.TryGetValue("Settings",out var settingsExpression)?StringValue(settingsExpression):null;
      int? count=fields.TryGetValue("ExpectedDiagnostics",out var diagnosticsExpression)?Count(diagnosticsExpression):0;
      int action=0;if(fields.TryGetValue("CodeActionIndex",out var actionExpression)){if(!TryEval(actionExpression,out var n)||n is not int number)continue;action=number;}
      if(input==null||count==null||(fields.ContainsKey("FixedCode")&&expected==null)||(fields.ContainsKey("Settings")&&settings==null))continue;
      if(method.ToString().Contains(".ExpectedDiagnostics.")||method.ToString().Contains(".TestState."))continue;
      fixtures.Add(new{label=caseLabel+"/object"+added++,analyzer,fix,source=input,expected,settings,diagnostics=count.Value,compilerDiagnostics=CompilerCount(diagnosticsExpression),compilerIds=CompilerIds(diagnosticsExpression),xmlReferences,language,actionIndex=action,useTabs=false,tabSize=4,indentationSize=4});
     }
     if(added==0)skipped.Add(caseLabel+": helper/configuration requires original harness");
    }
   }
  }
  Console.WriteLine(JsonSerializer.Serialize(new{fixtures,skipped},new JsonSerializerOptions{WriteIndented=true}));
 }
}
