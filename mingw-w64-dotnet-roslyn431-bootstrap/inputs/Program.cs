using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Threading.Tasks;

internal static class Program
{
    internal static void Require(bool condition, string message)
    {
        if (!condition) throw new Exception(message);
    }
    private static void Main(string[] args)
    {
        Require(CompilerChecks.Run(new[] { args[0], Path.Combine(args[1], "api-compiler-common.txt"), Path.Combine(args[1], "api-compiler-csharp.txt"), Path.Combine(args[1], "compiler-localization.json") }) == 0, "Compiler checks");
        using var manifest = JsonDocument.Parse(File.ReadAllText(args[3]));
        foreach (string name in new[] { "Microsoft.CodeAnalysis", "Microsoft.CodeAnalysis.CSharp" })
        {
            var assembly = Assembly.Load(name);
            var expected = manifest.RootElement.GetProperty(name).GetProperty("friend_attributes").EnumerateArray()
                .Select(e => e.GetString()).Where(s => s.StartsWith("[assembly: System.Runtime.CompilerServices.InternalsVisibleTo("))
                .Select(s => JsonSerializer.Deserialize<string>(s.Substring(s.IndexOf('(') + 1, s.Length - s.IndexOf('(') - 3)))
                .Distinct().OrderBy(s => s).ToArray();
            var actual = assembly.GetCustomAttributes<InternalsVisibleToAttribute>().Select(e => e.AssemblyName).OrderBy(s => s).ToArray();
            Require(expected.SequenceEqual(actual), "Original compiler friends: " + name);
            Require(assembly.GetCustomAttribute<global::System.Runtime.Versioning.TargetFrameworkAttribute>().FrameworkName == ".NETStandard,Version=v2.0", "Original NS2 compiler target");
        }
        Require(StandardConsumer.Probe() == Microsoft.CodeAnalysis.LanguageNames.CSharp, "Fresh netstandard2.0 API consumer");
        Console.WriteLine("PASS Roslyn4.3.1 netstandard2.0 compiler closure");
    }
}
