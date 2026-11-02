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
        await CompilerChecks.Run(new[] { args[1], args[0] });
        await WorkspaceChecks.Run(new[] { args[2], args[3], args[0] });
        var vb = typeof(VisualBasicCompilation).Assembly;
        using var inventory = JsonDocument.Parse(File.ReadAllText(args[4]));
        var expected = inventory.RootElement.GetProperty("Microsoft.CodeAnalysis.VisualBasic")
            .GetProperty("friends").EnumerateArray().Select(e => e.GetString()).OrderBy(e => e).ToArray();
        var actual = vb.GetCustomAttributes<InternalsVisibleToAttribute>().Select(e => e.AssemblyName).OrderBy(e => e).ToArray();
        int declarations = expected.Length;
        expected = expected.Distinct().ToArray();
        Require(expected.SequenceEqual(actual), "Original compiler friend identities");
        Console.WriteLine($"PASS {declarations} original compiler friend declarations / {actual.Length} unique emitted identities");
        var provider = typeof(Compilation).Assembly.GetType("Microsoft.CodeAnalysis.CommonMessageProvider", throwOnError: true);
        Require(provider.GetMethod("ShouldAssertExpectedMessageArgumentsLength", BindingFlags.Instance | BindingFlags.NonPublic) == null,
            "Release Common must omit the DEBUG-only abstract member");
        foreach (string name in new[] { "Embedded.vb", "InternalXmlHelper.vb", "VbCoreSourceText.vb", "VbMyTemplateText.vb" })
        {
            using var resource = vb.GetManifestResourceStream(name) ?? throw new Exception(name);
            using var bytes = new MemoryStream(); resource.CopyTo(bytes);
            var original = File.ReadAllText(Path.Combine(args[7], name)).Replace("\r\n", "\n").Replace("\n", "\r\n");
            var raw = File.ReadAllBytes(Path.Combine(args[7], name));
            // Preserve any original BOM, just as the build's byte normalization does.
            var expectedBytes = System.Text.Encoding.UTF8.GetBytes(original);
            if (raw.Length >= 3 && raw[0] == 0xef && raw[1] == 0xbb && raw[2] == 0xbf)
                expectedBytes = new byte[] { 0xef, 0xbb, 0xbf }.Concat(expectedBytes).ToArray();
            Require(bytes.ToArray().SequenceEqual(expectedBytes), "Original embedded template " + name);
        }
        var framework = Directory.GetFiles(args[0], "*.dll").Select(p => MetadataReference.CreateFromFile(p)).ToArray();
        var dependencies = Directory.GetFiles(AppContext.BaseDirectory, "*.dll").Where(p => p != vb.Location).ToArray();
        CheckApi.Run(framework, vb.Location, args[5], dependencies);
        var workspace = Assembly.Load("Microsoft.CodeAnalysis.VisualBasic.Workspaces");
        CheckApi.Run(framework, workspace.Location, args[6], dependencies.Where(p => p != workspace.Location).Append(vb.Location).ToArray());
        Console.WriteLine("PASS original VB4.14 compiler, Workspaces and API contracts");
    }
}
