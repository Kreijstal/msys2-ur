using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Microsoft.Build.Evaluation;

internal static class Program
{
    public static int Main(string[] args)
    {
        var paths = JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(args[0]))!;
        using var collection = new ProjectCollection();
        var result = new Dictionary<string, object>();
        string[] properties = { "BootstrapOriginalProjectDirectory", "AssemblyName", "AssemblyVersion", "MajorVersion", "StrongNameKeyId", "DefineConstants",
            "TargetFramework", "CLSCompliant", "NoWarn", "IsReferenceAssemblyProject", "GenFacadesForceZeroVersionSeeds", "TargetFrameworks", "IsPartialFacadeAssembly", "GeneratePlatformNotSupportedAssemblyMessage", "StringResourcesPath", "RootNamespace", "Nullable", "LangVersion", "AllowUnsafeBlocks", "EnableLibraryImportGenerator", "DisableImplicitFrameworkReferences", "StringResourcesName", "StringResourcesClassName", "StringResourcesNamespace", "OmitResources", "GenerateResxSourceOmitGetResourceString", "IsTrimmable", "ILLinkTrimAssembly", "ILLinkRewritePDBs", "ILLinkDisableIPConstProp", "ILLinkSubstitutionsLibraryBuildXml", "DeterministicSourcePaths", "LinkerNoWarn", "SkipLocalsInit", "RemoveIntegerChecks", "OptionStrict", "OptionExplicit", "OptionInfer", "ILLinkDescriptorsXml", "ILLinkSubstitutionsXml", "ILLinkLinkAttributesXml", "GenerateResourcesSubstitutions", "Language" };
        string[] kinds = { "Compile", "ProjectReference", "Reference", "ForwardedType", "AssemblyAttribute", "EmbeddedResource", "AdditionalFiles", "GenFacadesOmitType", "SeedTypePreference", "AsnXml", "EnabledGenerators", "ILLinkDescriptorsXmls", "ILLinkSubstitutionsXmls", "ILLinkLinkAttributesXmls", "ILLinkDescriptorsLibraryBuildXml", "ILLinkSuppressionsLibraryBuildXml" };
        foreach (var pair in paths)
        {
            var project = new Project(pair.Value, null, null, collection);
            string OriginalSourcePath(ProjectItem item) {
                string path = item.EvaluatedInclude;
                if (Path.IsPathRooted(path)) return item.GetMetadataValue("FullPath");
                return Path.GetFullPath(Path.Combine(project.GetPropertyValue("BootstrapOriginalProjectDirectory"), path));
            }
            var items = new Dictionary<string, object>();
            foreach (string kind in kinds)
                items.Add(kind, project.GetItems(kind).Select(item => new {
                    identity = item.EvaluatedInclude,
                    full_path = kind == "Compile" || kind == "ProjectReference" || kind == "EmbeddedResource" || kind == "AdditionalFiles" ? OriginalSourcePath(item) : "",
                    original_evaluated_full_path = item.GetMetadataValue("FullPath"),
                    metadata = item.Metadata.ToDictionary(m => m.Name, m => m.EvaluatedValue)
                }).ToArray());
            result.Add(pair.Key, new { properties = properties.ToDictionary(p => p, project.GetPropertyValue), items });
            collection.UnloadProject(project);
            Console.WriteLine("Evaluated " + pair.Key);
        }
        File.WriteAllText(args[1], JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }) + "\n");
        return 0;
    }
}
