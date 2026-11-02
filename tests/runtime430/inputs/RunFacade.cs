using System;
using System.IO;
using System.Runtime.Loader;
using System.Security.Cryptography;

static class Program
{
    static void Main(string[] args)
    {
        string path = Path.GetFullPath(args[0]);
        if (Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant() != args[1]) throw new Exception("Exact source facade bytes");
        var context = new AssemblyLoadContext("source-legacy-runtime-facade", isCollectible: true);
        try
        {
            var facade = context.LoadFromAssemblyPath(path);
            if (facade.GetName().FullName != "System.Runtime, Version=4.1.1.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a") throw new Exception("Original facade identity");
            foreach (var type in new[] { typeof(object), typeof(string), typeof(Guid), typeof(Uri), typeof(Func<int,int,int,int,int,int,int,int,int,int>) })
                if (facade.GetType(type.FullName!, throwOnError: true) != type) throw new Exception("Forwarded type: " + type);
            Type uriType = facade.GetType("System.Uri", true)!;
            object uri = Activator.CreateInstance(uriType, new object[] { "https://example.invalid/source-facade" })!;
            if ((string)uriType.GetProperty("Host")!.GetValue(uri)! != "example.invalid") throw new Exception("Forwarded Uri constructor/property");
            if (facade.Location != path) throw new Exception("Source facade location");
            Console.WriteLine("PASS exact source NET462 Runtime facade resolves five original core/System/System.Core forwards and executes Uri constructor/property on source NET8");
        }
        finally { context.Unload(); }
    }
}
