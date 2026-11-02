using System;
using System.IO;
using System.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
static class Program
{
    static void Main(string[] args)
    {
        var forwarded=new[]{"Matrix3x2","Matrix4x4","Plane","Quaternion","Vector2","Vector3","Vector4"};
        var root=CSharpSyntaxTree.ParseText(File.ReadAllText(args[0])).GetRoot();var remove=root.DescendantNodes().OfType<StructDeclarationSyntax>().Where(t=>forwarded.Contains(t.Identifier.ValueText)).ToArray();
        if(remove.Length!=7)throw new Exception("Original partial facade must remove exactly seven original forwarded struct definitions");
        File.WriteAllText(args[1],root.RemoveNodes(remove,SyntaxRemoveOptions.KeepNoTrivia)!.ToFullString());Console.WriteLine("PASS partial-reference source projection: "+string.Join(",",remove.Select(t=>t.Identifier.ValueText)));
    }
}
