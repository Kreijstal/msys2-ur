using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;

internal static class ApiGate
{
    static readonly SymbolDisplayFormat TypeFormat=SymbolDisplayFormat.FullyQualifiedFormat
        .WithGlobalNamespaceStyle(SymbolDisplayGlobalNamespaceStyle.Omitted)
        .WithMiscellaneousOptions(SymbolDisplayMiscellaneousOptions.UseSpecialTypes|SymbolDisplayMiscellaneousOptions.IncludeNullableReferenceTypeModifier);
    static bool Public(ISymbol symbol)=>symbol.DeclaredAccessibility is Accessibility.Public or Accessibility.Protected or Accessibility.ProtectedOrInternal;
    static Dictionary<string,string> Surface(IAssemblySymbol assembly)
    {
        var result=new Dictionary<string,string>();
        string Type(ITypeSymbol t)=>t.ToDisplayString(TypeFormat);
        void Add(ISymbol symbol)
        {
            string? id=symbol.GetDocumentationCommentId();if(id==null)return;
            string shape=symbol.DeclaredAccessibility+"|"+symbol.Kind;
            if(symbol is IMethodSymbol m)
                shape+="|"+Type(m.ReturnType)+"|ref="+m.ReturnsByRef+"|readonly="+m.ReturnsByRefReadonly;
            if(symbol is IPropertySymbol p)
                shape+="|"+Type(p.Type)+"|ref="+p.ReturnsByRef+"|readonly="+p.ReturnsByRefReadonly+"|get="+(p.GetMethod!=null&&Public(p.GetMethod))+"|set="+(p.SetMethod!=null&&Public(p.SetMethod));
            if(symbol is IFieldSymbol f)shape+="|"+Type(f.Type)+"|const="+f.IsConst+"|readonly="+f.IsReadOnly+"|value="+f.ConstantValue;
            if(symbol is IEventSymbol e)shape+="|"+Type(e.Type);
            if(symbol is INamedTypeSymbol n)shape+="|"+n.TypeKind+"|readonly="+n.IsReadOnly+"|reflike="+n.IsRefLikeType;
            result.Add(id,shape);
        }
        void VisitType(INamedTypeSymbol type)
        {
            if(!Public(type))return;Add(type);
            foreach(var member in type.GetMembers())
            {
                if(member is INamedTypeSymbol nested){VisitType(nested);continue;}
                if(!Public(member)||member.Name=="value__")continue;
                if(member is IMethodSymbol m && m.AssociatedSymbol!=null)continue;
                Add(member);
            }
        }
        void VisitNamespace(INamespaceSymbol ns)
        {
            foreach(var type in ns.GetTypeMembers())VisitType(type);
            foreach(var child in ns.GetNamespaceMembers())VisitNamespace(child);
        }
        VisitNamespace(assembly.GlobalNamespace);return result;
    }
    static IAssemblySymbol Metadata(string target,IEnumerable<string> references)
    {
        var own=MetadataReference.CreateFromFile(target);
        var compilation=CSharpCompilation.Create("MetadataApiGate",references:references.Where(p=>Path.GetFullPath(p)!=Path.GetFullPath(target)).Select(p=>MetadataReference.CreateFromFile(p)).Append(own),options:new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary,metadataImportOptions:MetadataImportOptions.All));
        return (IAssemblySymbol)compilation.GetAssemblyOrModuleSymbol(own)!;
    }
    internal static int CompareMetadata(string name,string expected,string actual,IEnumerable<string> expectedRefs,IEnumerable<string> actualRefs)
        =>Compare(name,Surface(Metadata(expected,expectedRefs)),Surface(Metadata(actual,actualRefs)));
    internal static int CompareSource(string name,IEnumerable<string> files,IEnumerable<string> defines,string actual,IEnumerable<string> references)
    {
        var options=new CSharpParseOptions(LanguageVersion.Preview,preprocessorSymbols:defines.Where(s=>s.Length!=0).Distinct());
        var trees=files.Select(p=>CSharpSyntaxTree.ParseText(File.ReadAllText(p),options,p));
        var compilation=CSharpCompilation.Create(name,trees,references.Where(p=>Path.GetFileNameWithoutExtension(p)!=name).Select(p=>MetadataReference.CreateFromFile(p)),new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary,allowUnsafe:true,nullableContextOptions:NullableContextOptions.Enable));
        var errors=compilation.GetDiagnostics().Where(d=>d.Severity==DiagnosticSeverity.Error).ToArray();
        if(errors.Length!=0)throw new Exception("Original API source compilation: "+name+Environment.NewLine+string.Join(Environment.NewLine,errors.Select(e=>e.ToString())));
        return Compare(name,Surface(compilation.Assembly),Surface(Metadata(actual,references)));
    }
    static int Compare(string name,Dictionary<string,string> expected,Dictionary<string,string> actual)
    {
        var missing=expected.Keys.Except(actual.Keys).ToArray();var extra=actual.Keys.Except(expected.Keys).ToArray();
        var changed=expected.Keys.Intersect(actual.Keys).Where(k=>expected[k]!=actual[k]).Select(k=>k+" expected="+expected[k]+" actual="+actual[k]).ToArray();
        if(missing.Length+extra.Length+changed.Length!=0)throw new Exception("Public API mismatch: "+name+"\nmissing="+string.Join("\n",missing)+"\nextra="+string.Join("\n",extra)+"\nchanged="+string.Join("\n",changed));
        Console.WriteLine($"PASS {name}: all {expected.Count} original public/protected declarations and checked shapes");
        return expected.Count;
    }
}
