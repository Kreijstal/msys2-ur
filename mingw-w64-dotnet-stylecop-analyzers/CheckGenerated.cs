using System;
using System.IO;
using System.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;

static class CheckGenerated
{
 public static void Verify(string source,string prepared)
 {
  bool compact=Directory.Exists(Path.Combine(source,"operation"));
  string baseline=compact?source:Path.Combine(source,"StyleCop.Analyzers/StyleCop.Analyzers/Lightup/.generated/StyleCop.Analyzers.CodeGeneration");
  string regenerated=compact?prepared:Path.Combine(prepared,"StyleCop.Analyzers/generated/StyleCop.Analyzers.CodeGeneration");
  int checkedFiles=0;
  foreach(string generator in new[]{"OperationLightupGenerator","SyntaxLightupGenerator"})
  {
   string folder=compact?(generator=="OperationLightupGenerator"?"operation":"syntax"):"StyleCop.Analyzers.CodeGeneration."+generator;
   var expected=Directory.GetFiles(Path.Combine(baseline,folder),"*.cs").ToDictionary(Path.GetFileName);
   var actual=Directory.GetFiles(Path.Combine(regenerated,folder),"*.cs").ToDictionary(Path.GetFileName);
   if(!expected.Keys.OrderBy(x=>x).SequenceEqual(actual.Keys.OrderBy(x=>x)))throw new Exception("Generated source file inventory: "+generator);
   foreach(var file in expected)
   {
    // Roslyn 4.9 NormalizeWhitespace inserts additional blank lines. Compare
    // C# tokens exactly, including literal spelling; never strip string contents.
    string baselineText=File.ReadAllText(file.Value);
    if(generator=="SyntaxLightupGenerator" && file.Key is "FileScopedNamespaceDeclarationSyntaxWrapper.g.cs" or "ForEachVariableStatementSyntaxWrapper.g.cs" or "LocalFunctionStatementSyntaxWrapper.g.cs" or "RecordDeclarationSyntaxWrapper.g.cs")
    {
     // These four wrappers inherit nodes whose AttributeLists/Modifiers
     // became real properties after Roslyn 1.2. The upstream generator now
     // accesses those properties instead of the old reflection extensions.
     string ReplaceOnce(string text,string before,string after)
     {
      if(text.Split(before).Length!=2)throw new Exception("Stale explicit generator adaptation: "+file.Key+"/"+before);
      return text.Replace(before,after);
     }
     baselineText=ReplaceOnce(baselineText,"this.SyntaxNode.AttributeLists()","this.SyntaxNode.AttributeLists");
     if(file.Key is "FileScopedNamespaceDeclarationSyntaxWrapper.g.cs" or "RecordDeclarationSyntaxWrapper.g.cs")baselineText=ReplaceOnce(baselineText,"this.SyntaxNode.Modifiers()","this.SyntaxNode.Modifiers");
    }
    string[] Tokens(string text)=>CSharpSyntaxTree.ParseText(text).GetRoot().DescendantTokens().Select(t=>t.RawKind+":"+t.Text).ToArray();
    if(!Tokens(baselineText).SequenceEqual(Tokens(File.ReadAllText(actual[file.Key]))))throw new Exception("Regenerated C# token mismatch: "+file.Key);
    checkedFiles++;
   }
  }
  if(checkedFiles!=183)throw new Exception("Expected full pinned 183-file light-up generator output");
  Console.WriteLine("PASS both upstream generators regenerate all 183 pinned output files: 179 token-identical, four wrappers with six explicit newer-Roslyn property accesses; formatting trivia may differ");
 }
}
