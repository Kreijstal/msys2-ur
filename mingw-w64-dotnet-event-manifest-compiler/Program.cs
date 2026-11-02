using System;
using System.Collections.Generic;
using EventTraceKit.EventTracing;
using EventTraceKit.EventTracing.Compilation;
using EventTraceKit.EventTracing.Support;

internal sealed class ConsoleDiagnostics : IDiagnosticConsumer
{
    public void HandleDiagnostic(DiagnosticSeverity severity, SourceLocation location, string message)
    {
        Console.Error.WriteLine("{0}: {1}: {2}", location, severity, message);
    }
}

internal static class Program
{
    private static int Main(string[] args)
    {
        if (args.Length != 4) {
            Console.Error.WriteLine("usage: event-manifest-compiler EVENTMAN_XSD WINMETA_XML MANIFEST OUTPUT_BASE");
            return 2;
        }
        try {
            var diagnostics = new DiagnosticsEngine(new ConsoleDiagnostics());
            var parser = EventManifestParser.CreateWithWinmeta(diagnostics, args[0], args[1]);
            if (parser == null || diagnostics.ErrorOccurred) return 1;
            var manifest = parser.ParseManifest(args[2]);
            if (manifest == null || diagnostics.ErrorOccurred) return 1;
            var options = new CompilationOptions {
                Inputs = new List<string> { args[2] }, OutputBaseName = args[3],
            };
            options.CodeGenOptions.GenerateCode = false;
            options.InferUnspecifiedOutputFiles();
            var compilation = EventManifestCompilation.Create(diagnostics, options);
            if (!compilation.AddManifests(manifest) || !compilation.Emit()) return 1;
            Console.WriteLine("Compiled event resources: " + args[3]);
            return 0;
        } catch (Exception error) {
            Console.Error.WriteLine(error);
            return 1;
        }
    }
}
