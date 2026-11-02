using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;

sealed class OwnedContext(string directory) : AssemblyLoadContext("owned-old-implementations", true)
{
    protected override Assembly? Load(AssemblyName name)
    {
        if (name.Name is not ("System.Collections.Immutable" or "System.Reflection.Metadata")) return null;
        string path = Path.Combine(directory, name.Name + ".dll");
        if (AssemblyName.GetAssemblyName(path).FullName != name.FullName) throw new Exception("Dependency identity mismatch: " + name);
        return LoadFromAssemblyPath(path);
    }
}

static class Program
{
    static void Main(string[] args)
    {
        string directory = Path.GetFullPath(args[0]);
        var context = new OwnedContext(directory);
        try
        {
            var bridge = context.LoadFromAssemblyPath(Path.Combine(directory, "Bridge.dll"));
            Console.WriteLine(bridge.GetType("Bridge")!.GetMethod("Run")!.Invoke(null, null));
            foreach (string name in new[] { "System.Collections.Immutable", "System.Reflection.Metadata" })
            {
                var loaded = context.Assemblies.Single(a => a.GetName().Name == name);
                if (loaded.Location != Path.Combine(directory, name + ".dll")) throw new Exception("Candidate implementation was not executed");
                Console.WriteLine("PASS exact candidate: " + loaded.FullName + " at " + loaded.Location);
            }
        }
        catch (TargetInvocationException e) { throw e.InnerException!; }
        finally { context.Unload(); }
    }
}
