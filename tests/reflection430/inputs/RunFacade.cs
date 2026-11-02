using System;
using System.IO;
using System.Reflection;
using System.Runtime.Loader;
using System.Security.Cryptography;

static class Program
{
    static void Main(string[] args)
    {
        string path = Path.GetFullPath(args[0]);
        string digest = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
        if (digest != args[1]) throw new Exception("Exact source facade bytes");
        var context = new AssemblyLoadContext("source-legacy-reflection-facade", isCollectible: true);
        try
        {
            var facade = context.LoadFromAssemblyPath(path);
            if (facade.GetName().FullName != "System.Reflection, Version=4.1.1.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a") throw new Exception("Original facade identity");
            foreach (var type in new[] { typeof(AssemblyName), typeof(MethodInfo), typeof(TypeInfo), typeof(ParameterInfo), typeof(BindingFlags) })
                if (facade.GetType(type.FullName!, throwOnError: true) != type) throw new Exception("Forwarded type: " + type);
            Type nameType = facade.GetType("System.Reflection.AssemblyName", throwOnError: true)!;
            object name = Activator.CreateInstance(nameType, new object[] { "SourceFacadeProbe" })!;
            if ((string)nameType.GetProperty("Name")!.GetValue(name)! != "SourceFacadeProbe") throw new Exception("Forwarded constructor/property");
            if (facade.Location != path || nameType.Assembly != typeof(object).Assembly) throw new Exception("Source NET8 resolution");
            Console.WriteLine("PASS exact source NET462 facade resolves five core reflection forwards and executes AssemblyName constructor/property on source NET8");
        }
        finally { context.Unload(); }
    }
}
