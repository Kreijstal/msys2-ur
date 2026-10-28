using System;
using Microsoft.PowerShell.MarkdownRender;

static void Require(bool condition, string message)
{
    if (!condition) throw new Exception(message);
}
var options = new PSMarkdownOptionInfo();
var html = MarkdownConverter.Convert("# Header\n\n**bold** and [link](https://example.org/)\n", MarkdownConversionType.HTML, options);
Require(html.Html.Contains("<strong>bold</strong>"), "HTML emphasis missing");
Require(html.Html.Contains("href=\"https://example.org/\""), "HTML link missing");
Require(html.Tokens.Count >= 2, "Markdown AST missing");
var terminal = MarkdownConverter.Convert("# Header\n\n**bold**\n\n```text\nhello\n```\n", MarkdownConversionType.VT100, options);
Require(terminal.VT100EncodedString.Contains("Header") && terminal.VT100EncodedString.Contains("hello"), "Terminal content missing");
Require(terminal.VT100EncodedString.Contains('\u001b'), "Terminal formatting escapes missing");
var identity = typeof(MarkdownConverter).Assembly.GetName();
Require(Convert.ToHexString(identity.GetPublicKeyToken()).ToLowerInvariant() == "31bf3856ad364e35", "Incorrect signing identity");
Console.WriteLine("PASS: PowerShell MarkdownRender HTML, terminal escapes, AST and signing identity");
