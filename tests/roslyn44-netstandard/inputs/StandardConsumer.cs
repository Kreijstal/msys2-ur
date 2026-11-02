using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Host.Mef;
public static class StandardConsumer
{
    public static string Probe()
    {
        var tree = CSharpSyntaxTree.ParseText("class FromStandard {}", new CSharpParseOptions(LanguageVersion.CSharp11));
        var host = MefHostServices.Create(new[] { typeof(Microsoft.CodeAnalysis.Workspace).Assembly, typeof(Microsoft.CodeAnalysis.CSharp.Formatting.CSharpFormattingOptions).Assembly });
        using (var workspace = new Microsoft.CodeAnalysis.AdhocWorkspace(host))
            return tree.GetRoot().Language;
    }
}
