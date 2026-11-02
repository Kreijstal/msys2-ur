using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;

internal static class ApiGate
{
    static readonly SymbolDisplayFormat TypeFormat=SymbolDisplayFormat.FullyQualifiedFormat
        .WithGlobalNamespaceStyle(SymbolDisplayGlobalNamespaceStyle.Omitted)
        .WithMiscellaneousOptions(SymbolDisplayMiscellaneousOptions.UseSpecialTypes|SymbolDisplayMiscellaneousOptions.IncludeNullableReferenceTypeModifier);
    static bool Public(ISymbol symbol)=>symbol.DeclaredAccessibility is Accessibility.Public or Accessibility.Protected or Accessibility.ProtectedOrInternal;
    static Dictionary<string,string> Surface(IAssemblySymbol assembly,Dictionary<string,string>? inherited=null,bool nullableAnnotations=false)
    {
        var result=new Dictionary<string,string>();
        string Type(ITypeSymbol t)=>t.ToDisplayString(nullableAnnotations ? TypeFormat : TypeFormat.WithMiscellaneousOptions(SymbolDisplayMiscellaneousOptions.UseSpecialTypes));
        void Add(ISymbol symbol,string? idOverride=null,Dictionary<string,string>? destination=null)
        {
            string? id=idOverride??symbol.GetDocumentationCommentId();if(id==null)return;
            string shape=symbol.DeclaredAccessibility+"|"+symbol.Kind+"|static="+symbol.IsStatic+"|abstract="+symbol.IsAbstract+"|virtual="+symbol.IsVirtual+"|override="+symbol.IsOverride+"|sealed="+symbol.IsSealed;
            if(symbol is IMethodSymbol m)
                shape+="|"+Type(m.ReturnType)+"|ref="+m.ReturnsByRef+"|readonly="+m.ReturnsByRefReadonly+"|params="+string.Join(";",m.Parameters.Select(p=>Type(p.Type)+":"+p.RefKind+":"+p.IsParams+":"+p.IsOptional+":"+p.HasExplicitDefaultValue+":"+(p.HasExplicitDefaultValue?JsonSerializer.Serialize(p.ExplicitDefaultValue):"")));
            if(symbol is IPropertySymbol p)
                shape+="|"+Type(p.Type)+"|ref="+p.ReturnsByRef+"|readonly="+p.ReturnsByRefReadonly+"|get="+(p.GetMethod!=null&&Public(p.GetMethod))+"|set="+(p.SetMethod!=null&&Public(p.SetMethod));
            if(symbol is IFieldSymbol f)shape+="|"+Type(f.Type)+"|const="+f.IsConst+"|readonly="+f.IsReadOnly+"|value="+f.ConstantValue;
            if(symbol is IEventSymbol e)shape+="|"+Type(e.Type);
            if(symbol is INamedTypeSymbol n)shape+="|"+n.TypeKind+"|readonly="+n.IsReadOnly+"|reflike="+n.IsRefLikeType+"|base="+(n.BaseType==null?"":Type(n.BaseType))+"|interfaces="+string.Join(";",n.Interfaces.Select(Type).OrderBy(x=>x));
            (destination??result)[id]=shape;
        }
        void VisitType(INamedTypeSymbol type)
        {
            if(!Public(type))return; for(var parent=type.ContainingType;parent!=null;parent=parent.ContainingType)if(!Public(parent))return;Add(type);
            if(inherited!=null) {
                string owner=type.GetDocumentationCommentId()!.Substring(2);
                for(var ancestor=type.BaseType;ancestor!=null;ancestor=ancestor.BaseType) {
                    string prefix=ancestor.OriginalDefinition.GetDocumentationCommentId()!.Substring(2)+".";
                    foreach(var member in ancestor.GetMembers()) {
                        if(!Public(member)||member is INamedTypeSymbol)continue;
                        if(member is IMethodSymbol method && (method.MethodKind is MethodKind.Constructor or MethodKind.StaticConstructor || method.AssociatedSymbol!=null))continue;
                        string? id=member.GetDocumentationCommentId();
                        if(id==null||!id.Substring(2).StartsWith(prefix,StringComparison.Ordinal))continue;
                        string projected=id.Substring(0,2)+owner+"."+id.Substring(2+prefix.Length);
                        if(!inherited.ContainsKey(projected))Add(member,projected,inherited);
                    }
                }
            }
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
        VisitNamespace(assembly.GlobalNamespace);foreach(var type in assembly.GetForwardedTypes())VisitType(type);return result;
    }
    static IAssemblySymbol Metadata(string target,IEnumerable<string> references)
    {
        var own=MetadataReference.CreateFromFile(target);
        var compilation=CSharpCompilation.Create("MetadataApiGate",references:references.Where(p=>Path.GetFullPath(p)!=Path.GetFullPath(target)).Select(p=>MetadataReference.CreateFromFile(p)).Append(own),options:new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary,metadataImportOptions:MetadataImportOptions.All));
        return (IAssemblySymbol)compilation.GetAssemblyOrModuleSymbol(own)!;
    }
    public static int Main(string[] args)
    {
        string[] refs=Directory.GetFiles(args[2],"*.dll");
        var expected=Surface(Metadata(args[0],refs));
        var inherited=new Dictionary<string,string>();
        var actual=Surface(Metadata(args[1],refs),inherited);
        foreach(string id in expected.Keys.Where(k=>!actual.ContainsKey(k)&&inherited.ContainsKey(k)))actual.Add(id,inherited[id]);
        var missing=expected.Keys.Except(actual.Keys).OrderBy(x=>x).ToArray();
        var extra=actual.Keys.Except(expected.Keys).OrderBy(x=>x).ToArray();
        var changed=expected.Keys.Intersect(actual.Keys).Where(k=>expected[k]!=actual[k]).Select(k=>new{id=k,expected=expected[k],actual=actual[k]}).ToArray();
        var annotatedExpected=Surface(Metadata(args[0],refs),nullableAnnotations:true);
        var annotatedActual=Surface(Metadata(args[1],refs),nullableAnnotations:true);
        var annotationDifferences=annotatedExpected.Keys.Intersect(annotatedActual.Keys).Where(k=>annotatedExpected[k]!=annotatedActual[k]).Select(k=>new{id=k,expected=annotatedExpected[k],actual=annotatedActual[k]}).ToArray();
        string[] originalObliviousMembers={"M:System.CodeDom.CodeTypeReference.#ctor(System.String)","M:System.CodeDom.CodeTypeReference.#ctor(System.String,System.CodeDom.CodeTypeReferenceOptions)","P:System.CodeDom.CodeTypeReference.ArrayElementType"};
        bool originalObliviousAnnotationOnly=annotationDifferences.Length==3 && annotationDifferences.All(d=>originalObliviousMembers.Contains(d.id) && d.expected==d.actual.Replace("?",""));
        int differences=missing.Length+extra.Length+changed.Length;
        File.WriteAllText(args[3],JsonSerializer.Serialize(new{expected_entries=expected.Count,actual_entries=actual.Count,missing,extra,changed,total_differences=differences,nullable_annotation_differences=annotationDifferences,strict_nullable_metadata_equal=annotationDifferences.Length==0,original_nullable_oblivious_reference_with_shared_source_annotations=originalObliviousAnnotationOnly,full_dependency_goal_complete=false},new JsonSerializerOptions{WriteIndented=true})+"\n");
        Console.WriteLine("CodeDom NET9 CLR API: expected="+expected.Count+" missing="+missing.Length+" extra="+extra.Length+" changed="+changed.Length+";original nullable annotation differences="+annotationDifferences.Length);
        return differences==0 && originalObliviousAnnotationOnly?0:1;
    }
}
