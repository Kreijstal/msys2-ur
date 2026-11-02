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
    static Dictionary<string,string> Surface(IAssemblySymbol assembly,Dictionary<string,string>? inherited=null)
    {
        var result=new Dictionary<string,string>();
        string Type(ITypeSymbol t)=>t.ToDisplayString(TypeFormat);
        void Add(ISymbol symbol,string? idOverride=null,Dictionary<string,string>? destination=null)
        {
            string? id=idOverride??symbol.GetDocumentationCommentId();if(id==null)return;
            string shape=symbol.DeclaredAccessibility+"|"+symbol.Kind;
            if(symbol is IMethodSymbol m)
                shape+="|"+Type(m.ReturnType)+"|ref="+m.ReturnsByRef+"|readonly="+m.ReturnsByRefReadonly;
            if(symbol is IPropertySymbol p)
                shape+="|"+Type(p.Type)+"|ref="+p.ReturnsByRef+"|readonly="+p.ReturnsByRefReadonly+"|get="+(p.GetMethod!=null&&Public(p.GetMethod))+"|set="+(p.SetMethod!=null&&Public(p.SetMethod));
            if(symbol is IFieldSymbol f)shape+="|"+Type(f.Type)+"|const="+f.IsConst+"|readonly="+f.IsReadOnly+"|value="+f.ConstantValue;
            if(symbol is IEventSymbol e)shape+="|"+Type(e.Type);
            if(symbol is INamedTypeSymbol n)shape+="|"+n.TypeKind+"|readonly="+n.IsReadOnly+"|reflike="+n.IsRefLikeType;
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
        string plan=args[0], output=args[1], refDir=args[2];
        var status=JsonDocument.Parse(File.ReadAllText(Path.Combine(plan,"build-status.json")));
        var names=status.RootElement.EnumerateObject().Where(p=>p.Value.GetProperty("kind").GetString()!="stub" && File.Exists(Path.Combine(refDir,p.Name+".dll"))).Select(p=>p.Name).ToArray();
        string[] expectedRefs=Directory.GetFiles(refDir,"*.dll");
        string[] actualRefs=Directory.GetFiles(Path.Combine(plan,"lib"),"*.dll").Append(args[3]).ToArray();
        var reports=new Dictionary<string,object>();int differences=0, entries=0;
        foreach(string name in names) {
            var expected=Surface(Metadata(Path.Combine(refDir,name+".dll"),expectedRefs));
            var inherited=new Dictionary<string,string>();
            var actual=Surface(Metadata(Path.Combine(plan,"lib",name+".dll"),actualRefs),inherited);
            var inheritedMatches=expected.Keys.Where(k=>!actual.ContainsKey(k)&&inherited.ContainsKey(k)).ToArray();
            foreach(string id in inheritedMatches)actual.Add(id,inherited[id]);
            var missing=expected.Keys.Except(actual.Keys).OrderBy(x=>x,StringComparer.Ordinal).ToArray();
            var extra=actual.Keys.Except(expected.Keys).OrderBy(x=>x,StringComparer.Ordinal).ToArray();
            var changed=expected.Keys.Intersect(actual.Keys).Where(k=>expected[k]!=actual[k]).Select(k=>new{id=k,expected=expected[k],actual=actual[k]}).ToArray();
            reports[name]=new{expected_entries=expected.Count,actual_entries=actual.Count,inherited_members_resolved=inheritedMatches,missing,extra,changed};
            differences+=missing.Length+extra.Length+changed.Length;entries+=expected.Count;
            Console.WriteLine(name+": expected="+expected.Count+" missing="+missing.Length+" extra="+extra.Length+" changed="+changed.Length);
        }
        File.WriteAllText(output,JsonSerializer.Serialize(new{assemblies=reports,expected_public_entries=entries,total_differences=differences,all_complete_framework_contracts_verified=false,full_dependency_goal_complete=false},new JsonSerializerOptions{WriteIndented=true})+"\n");
        return differences==0?0:1;
    }
}
