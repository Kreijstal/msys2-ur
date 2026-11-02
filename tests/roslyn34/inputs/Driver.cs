using System;
using System.IO;
using System.Reflection;
using System.Runtime.Loader;

sealed class CompilerContext(string directory) : AssemblyLoadContext("original-Roslyn-3.4", true)
{
    protected override Assembly? Load(AssemblyName name)
    {
        var path = Path.Combine(directory, name.Name + ".dll");
        if (!File.Exists(path)) return null;
        var actual = AssemblyName.GetAssemblyName(path);
        if (name.Version != null && actual.Version != name.Version)
            throw new InvalidOperationException($"Dependency version mismatch: {name} / {actual}");
        return LoadFromAssemblyPath(path);
    }
}

static class Driver
{
    static int Main(string[] args)
    {
        var folder = Environment.GetEnvironmentVariable("ROSLYN34_COMPILER_DIRECTORY")
            ?? throw new InvalidOperationException("ROSLYN34_COMPILER_DIRECTORY is required");
        var context = new CompilerContext(folder);
        try
        {
            var assembly = context.LoadFromAssemblyPath(Path.Combine(folder, "csc.dll"));
            return (int)assembly.GetType("CompilerEntry")!.GetMethod("Run")!.Invoke(null, [args])!;
        }
        catch (TargetInvocationException e)
        {
            Console.Error.WriteLine(e.InnerException);
            return 1;
        }
        finally { context.Unload(); }
    }
}
