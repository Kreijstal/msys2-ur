using System;
using System.Linq;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

public static class StandardRoslynConsumer
{
    public static string Run()
    {
        var tree=CSharpSyntaxTree.ParseText("public class StandardProbe { public int Sum(int left,int right) => left+right; }");
        var root=tree.GetRoot();var method=root.DescendantNodes().OfType<MethodDeclarationSyntax>().Single();
        if(method.Identifier.ValueText!="Sum" || method.ParameterList.Parameters.Count!=2)
            throw new Exception("Original netstandard2.0 syntax consumer");
        var options=new CSharpParseOptions(LanguageVersion.CSharp13);
        if(options.LanguageVersion!=LanguageVersion.CSharp13)
            throw new Exception("Original language API consumer");
        return "PASS original netstandard2.0 Roslyn syntax/options consumer";
    }
}
