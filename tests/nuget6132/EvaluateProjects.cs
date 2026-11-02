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
        string[] properties = { "AssemblyName", "RootNamespace", "DefineConstants", "TargetFramework", "NoWarn", "Language", "TargetFrameworks", "StartupObject", "ServerGarbageCollection", "TieredCompilation", "VBRuntime", "RootNamespace", "OptionStrict", "OptionInfer", "OptionExplicit", "RemoveIntegerChecks", "AssemblyVersion", "FileVersion", "InformationalVersion", "AssemblyOriginatorKeyFile", "NeutralLanguage", "Version", "SharedDirectory", "TargetFrameworksLibrary", "NoWarn", "TreatWarningsAsErrors", "WarningsNotAsErrors", "GenerateDocumentationFile", "AllowUnsafeBlocks", "Nullable" };
        string[] kinds = { "Compile", "ProjectReference", "PackageReference", "EmbeddedResource", "InternalsVisibleTo", "RestrictedInternalsVisibleTo", "Import", "PackageVersion" };
        foreach (var pair in paths)
        {
            var project = new Project(pair.Value, new Dictionary<string,string> { ["TargetFramework"] = "net10.0", ["Configuration"] = "Release" }, null, collection);
            var items = new Dictionary<string, object>();
            foreach (string kind in kinds)
                items.Add(kind, project.GetItems(kind).Select(item => new {
                    identity = item.EvaluatedInclude,
                    full_path = kind == "Compile" || kind == "ProjectReference" || kind == "EmbeddedResource" ? item.GetMetadataValue("FullPath") : "",
                    metadata = item.Metadata.ToDictionary(m => m.Name, m => m.EvaluatedValue)
                }).ToArray());
            result.Add(pair.Key, new { properties = properties.Distinct().ToDictionary(p => p, project.GetPropertyValue), items, imports = project.Imports.Select(i => i.ImportedProject.FullPath).Distinct().ToArray() });
            collection.UnloadProject(project);
            Console.WriteLine("Evaluated " + pair.Key);
        }
        File.WriteAllText(args[1], JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }) + "\n");
        return 0;
    }
}
