using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.VisualBasic;

internal static class Program
{
    internal static void Require(bool value, string message)
    {
        if (!value) throw new Exception(message);
    }
    private static async Task Main(string[] args)
    {
        await CompilerChecks.Run(new[] { args[0], args[1] });
        var vb = typeof(VisualBasicCompilation).Assembly;
        var references = Directory.GetFiles(args[1], "*.dll").Select(p => MetadataReference.CreateFromFile(p));
        CheckApi.Run(references, vb.Location, args[2], typeof(Compilation).Assembly.Location);
        using var inventory = JsonDocument.Parse(File.ReadAllText(args[3]));
        var expected = inventory.RootElement.GetProperty("friends").EnumerateArray().Select(e => e.GetString()).OrderBy(s => s).ToArray();
        var actual = vb.GetCustomAttributes<InternalsVisibleToAttribute>().Select(a => a.AssemblyName).OrderBy(s => s).ToArray();
        File.WriteAllText(args[3] + ".actual.json", JsonSerializer.Serialize(actual));
        Console.WriteLine($"Original VB friend declarations: {expected.Length}; emitted: {actual.Length}");
        foreach (var value in expected.Except(actual)) Console.WriteLine("Missing friend: " + value);
        foreach (var value in actual.Except(expected)) Console.WriteLine("Unexpected friend: " + value);
        Require(expected.Distinct().SequenceEqual(actual), "Original unique VB friend identities");
        Console.WriteLine($"PASS all {expected.Length} original VB friend declarations / {actual.Length} unique emitted identities");
        foreach (string name in new[] { "Embedded.vb", "InternalXmlHelper.vb", "VbCoreSourceText.vb", "VbMyTemplateText.vb" })
        {
            using var resource = vb.GetManifestResourceStream(name) ?? throw new Exception(name);
            using var stream = new MemoryStream(); resource.CopyTo(stream);
            Require(stream.ToArray().SequenceEqual(File.ReadAllBytes(Path.Combine(args[4], name))), "Original embedded template bytes: " + name);
        }
        Console.WriteLine("PASS four original embedded VB template byte sequences");
    }
}
