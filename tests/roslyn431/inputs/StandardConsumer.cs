using Microsoft.CodeAnalysis.CSharp;
public static class StandardConsumer
{
    public static string Probe()
    {
        var tree = CSharpSyntaxTree.ParseText("class FromStandard {}", new CSharpParseOptions(LanguageVersion.Preview));
        return tree.GetRoot().Language;
    }
}
