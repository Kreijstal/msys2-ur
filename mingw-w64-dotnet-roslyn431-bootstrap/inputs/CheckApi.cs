#nullable enable
// Symbol formatting follows the MIT-licensed PublicApiAnalyzers 3.3.4 format.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;

internal static class CheckApi
{
    private static readonly SymbolDisplayFormat Format = new(
        globalNamespaceStyle: SymbolDisplayGlobalNamespaceStyle.OmittedAsContaining,
        typeQualificationStyle: SymbolDisplayTypeQualificationStyle.NameAndContainingTypesAndNamespaces,
        propertyStyle: SymbolDisplayPropertyStyle.ShowReadWriteDescriptor,
        genericsOptions: SymbolDisplayGenericsOptions.IncludeTypeParameters,
        memberOptions: SymbolDisplayMemberOptions.IncludeParameters | SymbolDisplayMemberOptions.IncludeContainingType |
            SymbolDisplayMemberOptions.IncludeExplicitInterface | SymbolDisplayMemberOptions.IncludeModifiers | SymbolDisplayMemberOptions.IncludeConstantValue,
        parameterOptions: SymbolDisplayParameterOptions.IncludeExtensionThis | SymbolDisplayParameterOptions.IncludeParamsRefOut |
            SymbolDisplayParameterOptions.IncludeType | SymbolDisplayParameterOptions.IncludeName | SymbolDisplayParameterOptions.IncludeDefaultValue,
        miscellaneousOptions: SymbolDisplayMiscellaneousOptions.UseSpecialTypes | (SymbolDisplayMiscellaneousOptions)(1 << 6) |
            (SymbolDisplayMiscellaneousOptions)(1 << 8));

    internal static void Run(IEnumerable<MetadataReference> framework, string assembly, string baseline, params string[] extra)
    {
        bool trackNullability = File.ReadLines(baseline).Any(line => line.Trim() == "#nullable enable");
        var format = trackNullability ? Format : Format.WithMiscellaneousOptions(SymbolDisplayMiscellaneousOptions.UseSpecialTypes);
        // The older baseline spells native integers by their underlying CLR type.
        var addOptions = typeof(SymbolDisplayFormat).GetMethod("AddCompilerInternalOptions", BindingFlags.Instance | BindingFlags.NonPublic)!;
        var nativeUnderlying = Enum.Parse(addOptions.GetParameters()[0].ParameterType, "UseNativeIntegerUnderlyingType");
        format = (SymbolDisplayFormat)addOptions.Invoke(format, new[] { nativeUnderlying })!;

        var target = MetadataReference.CreateFromFile(assembly);
        var references = framework.Concat(extra.Where(p => Path.GetFullPath(p) != Path.GetFullPath(assembly)).Select(p => MetadataReference.CreateFromFile(p))).Append(target);
        var compilation = CSharpCompilation.Create("ApiGate", references: references,
            options: new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary, metadataImportOptions: MetadataImportOptions.All));
        var symbol = (IAssemblySymbol)compilation.GetAssemblyOrModuleSymbol(target)!;
        var actual = new HashSet<string>();
        string Display(ISymbol symbol) => string.Concat(symbol.ToDisplayParts(format).Select(part =>
            part.Kind == SymbolDisplayPartKind.Keyword && part.Symbol is ITypeSymbol { IsNativeIntegerType: true } type
                ? type.ToDisplayString(format.WithMiscellaneousOptions(format.MiscellaneousOptions & ~SymbolDisplayMiscellaneousOptions.UseSpecialTypes))
                : part.ToString()));

        string ExperimentalPrefix(ISymbol symbol) {
            for (ISymbol? current = symbol; current != null; current = current.ContainingSymbol) {
                var attributes = current.GetAttributes();
                foreach (var attribute in attributes)
                    if (attribute.AttributeClass?.ToDisplayString() == "System.Diagnostics.CodeAnalysis.ExperimentalAttribute" &&
                        attribute.ConstructorArguments.Length != 0 && attribute.ConstructorArguments[0].Value is string diagnosticId)
                        return "[" + diagnosticId + "]";
            }
            return "";
        }
        void Add(ISymbol member) {
            var signature = ExperimentalPrefix(member) + Display(member);
            ITypeSymbol? result = member switch {
                IMethodSymbol m => m.ReturnType, IFieldSymbol f => f.Type,
                IEventSymbol e => e.Type, _ => null,
            };
            if (result != null) signature += " -> " + Display(result);
            actual.Add(signature);
        }
        void Visit(INamespaceOrTypeSymbol container) {
            foreach (var member in container.GetMembers()) {
                if (member is INamespaceSymbol ns) { Visit(ns); continue; }
                if (member.DeclaredAccessibility is not (Accessibility.Public or Accessibility.Protected or Accessibility.ProtectedOrInternal)) continue;
                if (member is INamedTypeSymbol type) { Add(type); Visit(type); continue; }
                if (member is IPropertySymbol property) {
                    if (property.GetMethod is { DeclaredAccessibility: Accessibility.Public or Accessibility.Protected or Accessibility.ProtectedOrInternal } get) Add(get);
                    if (property.SetMethod is { DeclaredAccessibility: Accessibility.Public or Accessibility.Protected or Accessibility.ProtectedOrInternal } set) Add(set);
                } else Add(member);
            }
        }
        Visit(symbol.GlobalNamespace);
        var lines = File.ReadLines(baseline).Where(s => s.Length > 0 && !s.StartsWith('#')).ToArray();
        var removed = lines.Where(s => s.StartsWith("*REMOVED*")).Select(s => s[9..].TrimStart('~')).ToHashSet();
        var expected = lines.Where(s => !s.StartsWith("*REMOVED*")).Select(s => s.TrimStart('~')).Where(s => !removed.Contains(s)).Distinct().ToArray();
        var missing = expected.Where(s => !actual.Contains(s)).ToArray();
        if (missing.Length != 0)
            foreach (var entry in actual.Where(s => s.Contains("Microsoft.CodeAnalysis.ModuleMetadata.CreateFrom")).OrderBy(s => s))
                Console.Error.WriteLine("Actual metadata factory API: " + entry);

        foreach (var entry in missing.Take(30)) Console.Error.WriteLine("Missing public API: " + entry);
        Program.Require(missing.Length == 0, symbol.Name + ": " + missing.Length + " of " + expected.Length + " upstream API declarations missing");
        Console.WriteLine("PASS: " + symbol.Name + " preserves all " + expected.Length + " upstream public API declarations");
    }
}
