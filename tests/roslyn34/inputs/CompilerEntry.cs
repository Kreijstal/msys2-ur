// Bootstrap entry point for the original local Csc implementation.
// Compiler server and original Toolset packaging are separate unfinished work.
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CommandLine;
using Microsoft.CodeAnalysis.CSharp.CommandLine;

public static class CompilerEntry
{
    public static int Run(string[] args)
    {
        // Original BuildClient.Run performs this registration on CoreCLR.
        // Resolve through the original compiler's identity; the NET8 bootstrap
        // host must not bind this call to its framework CodePages 8 assembly.
        var name = typeof(Compilation).Assembly.GetReferencedAssemblies()
            .Single(reference => reference.Name == "System.Text.Encoding.CodePages");
        var assembly = Assembly.Load(name);
        var provider = (System.Text.EncodingProvider)assembly
            .GetType("System.Text.CodePagesEncodingProvider").GetProperty("Instance").GetValue(null);
        System.Text.Encoding.RegisterProvider(provider);
        var paths = new BuildPaths(Path.GetDirectoryName(typeof(CompilerEntry).Assembly.Location),
            Environment.CurrentDirectory, null, Path.GetTempPath());
        return Csc.Run(args, paths, Console.Out, new CoreClrAnalyzerAssemblyLoader());
    }
}
