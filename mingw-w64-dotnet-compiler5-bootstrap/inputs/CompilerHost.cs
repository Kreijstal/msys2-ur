// Host the installed source-built desktop compiler on the source .NET8 runtime.
using System;
using System.IO;
using System.Linq;
using System.Reflection;

internal static class CompilerHost
{
    public static int Main(string[] args)
    {
        Assembly compiler = Assembly.LoadFrom(Path.Combine(AppContext.BaseDirectory, "csc.exe"));
        Type program = compiler.GetType("Microsoft.CodeAnalysis.CSharp.CommandLine.Program", true)!;
        MethodInfo run = program.GetMethod("Run", BindingFlags.Public | BindingFlags.Static)!;
        Type loaderType = compiler.GetTypes().FirstOrDefault(t => t.Name == "AnalyzerAssemblyLoader" && !t.IsAbstract)
            ?? Assembly.Load("Microsoft.CodeAnalysis").GetTypes().First(t => t.Name == "AnalyzerAssemblyLoader" && !t.IsAbstract);
        object loader = Activator.CreateInstance(loaderType, nonPublic: true)!;
        try {
            return (int)run.Invoke(null, new object?[] { args, AppContext.BaseDirectory,
                Directory.GetCurrentDirectory(), null, Path.GetTempPath(), Console.Out, loader })!;
        } catch (TargetInvocationException error) when (error.InnerException != null) {
            Console.Error.WriteLine(error.InnerException);
            return 1;
        }
    }
}
