using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Resources;
using System.Runtime.Loader;
using System.Security.Cryptography;

internal static class Program
{
    static int Main(string[] args)
    {
        string path = Path.GetFullPath(args[0]);
        var context = new AssemblyLoadContext("portable-protecteddata44", isCollectible: true);
        context.LoadFromAssemblyPath(path);
        context.LoadFromAssemblyPath(typeof(Program).Assembly.Location).GetType("Program")!
            .GetMethod("Run", BindingFlags.NonPublic | BindingFlags.Static)!.Invoke(null, new object[] { path, args[1], args[2] });
        return 0;
    }
    static void Run(string path, string message, string resourceFile)
    {
        var assembly = typeof(ProtectedData).Assembly;
        if (assembly.Location != path || assembly.GetName().Version!.ToString() != "4.0.2.0" ||
            assembly.GetCustomAttribute<AssemblyFileVersionAttribute>()!.Version != "4.6.25519.03" ||
            assembly.GetCustomAttributesData().Any(a => a.AttributeType.FullName == "System.Runtime.Versioning.TargetFrameworkAttribute") ||
            !assembly.GetCustomAttributes<AssemblyMetadataAttribute>().Any(a => a.Key == "NotSupported" && a.Value == "True"))
            throw new Exception("original portable identity/metadata");
        foreach (Action action in new Action[] {
            () => ProtectedData.Protect(new byte[] { 1 }, null!, DataProtectionScope.CurrentUser),
            () => ProtectedData.Unprotect(new byte[] { 1 }, null!, DataProtectionScope.LocalMachine),
            () => ProtectedData.Protect(null!, null!, DataProtectionScope.CurrentUser) })
        {
            try { action(); }
            catch (PlatformNotSupportedException error) { if (error.Message == message) continue; throw; }
            throw new Exception("portable API must throw original PNSE message");
        }
        var expected = System.Text.Json.JsonSerializer.Deserialize<System.Collections.Generic.Dictionary<string, string>>(File.ReadAllText(resourceFile))!;
        using (var stream = assembly.GetManifestResourceStream("FxResources.System.Security.Cryptography.ProtectedData.SR.resources")!)
        using (var reader = new ResourceReader(stream))
        {
            int count = 0;
            foreach (DictionaryEntry entry in reader)
            {
                if (expected[(string)entry.Key] != (string)entry.Value!) throw new Exception("portable resource value");
                count++;
            }
            if (count != 2 || count != expected.Count) throw new Exception("complete portable resource set");
        }
        using (var pe = new PEReader(File.OpenRead(path)))
        using (var pdb = MetadataReaderProvider.FromPortablePdbStream(File.OpenRead(Path.ChangeExtension(path, ".pdb"))))
        {
            var cv = pe.ReadCodeViewDebugDirectoryData(pe.ReadDebugDirectory().Single(e => e.Type == DebugDirectoryEntryType.CodeView));
            if (cv.Guid != new Guid(pdb.GetMetadataReader().DebugMetadataHeader!.Id.Take(16).ToArray())) throw new Exception("portable PDB identity");
        }
        Console.WriteLine("PASS isolated original portable identity, NotSupported metadata, both APIs throwing original message, two resource values and PDB identity");
    }
}
