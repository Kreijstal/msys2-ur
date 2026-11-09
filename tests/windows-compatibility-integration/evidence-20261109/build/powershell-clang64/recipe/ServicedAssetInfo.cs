using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;

static class ServicedAssetInfo
{
    static int Main(string[] args)
    {
        var records = args.Skip(1).Select(path => new {
            name = Path.GetFileNameWithoutExtension(path),
            assembly_version = AssemblyName.GetAssemblyName(path).Version.ToString(),
            file_version = FileVersionInfo.GetVersionInfo(path).FileVersion,
            product_version = FileVersionInfo.GetVersionInfo(path).ProductVersion
        }).ToArray();
        File.WriteAllText(args[0], JsonSerializer.Serialize(records, new JsonSerializerOptions { WriteIndented = true }));
        return 0;
    }
}
