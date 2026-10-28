using System;
using Markdig;
using Markdig.Syntax;

static void Require(bool condition, string message)
{
    if (!condition) throw new Exception(message);
}
var pipeline = new MarkdownPipelineBuilder().UseAdvancedExtensions().Build();
var html = Markdown.ToHtml("# Heading\n\n**bold** and [link](https://example.org/)\n\n```text\n<a>&\n```\n", pipeline);
Require(html.Contains("<strong>bold</strong>"), "Strong emphasis missing");
Require(html.Contains("href=\"https://example.org/\""), "Link target missing");
Require(html.Contains("&lt;a&gt;&amp;"), "Code block escaping incorrect");
var table = Markdown.ToHtml("| A | B |\n|---|---|\n| 1 | 2 |\n", pipeline);
Require(table.Contains("<table>") && table.Contains("<td>2</td>"), "Table extension failed");
var ast = Markdown.Parse("# Header\n\n- first\n- second\n", pipeline);
Require(ast[0] is HeadingBlock && ast[1] is ListBlock, "AST node types incorrect");
var identity = typeof(Markdown).Assembly.GetName();
Require(identity.Version == new Version(0, 33, 0, 0), "Incorrect assembly version");
Require(Convert.ToHexString(identity.GetPublicKeyToken()).ToLowerInvariant() == "870da25a133885f8", "Incorrect signing identity");
Console.WriteLine("PASS: Markdig HTML, escaping, tables, AST and signing identity");
