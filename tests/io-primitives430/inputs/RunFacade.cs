using System;
using System.IO;
using System.Runtime.Loader;
using System.Security.Cryptography;

static class Program
{
    static void Main(string[] args)
    {
        string path = Path.GetFullPath(args[0]);
        if (Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant() != args[1]) throw new Exception("Source facade bytes");
        var context = new AssemblyLoadContext("source-legacy-io-facade", isCollectible: true);
        try
        {
            var facade = context.LoadFromAssemblyPath(path);
            if (facade.GetName().FullName != "System.IO, Version=4.1.1.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a") throw new Exception("Original facade identity");
            foreach (var type in new[] { typeof(Stream), typeof(MemoryStream), typeof(BinaryReader), typeof(TextReader), typeof(InvalidDataException) })
                if (facade.GetType(type.FullName!, throwOnError: true) != type) throw new Exception("Forwarded type: " + type);
            using var stream = (Stream)Activator.CreateInstance(facade.GetType("System.IO.MemoryStream", true)!)!;
            byte[] data = { 0, 127, 255, 42 };
            stream.Write(data, 0, data.Length); stream.Position = 0;
            foreach (byte value in data) if (stream.ReadByte() != value) throw new Exception("Forwarded IO data");
            if (stream.ReadByte() != -1 || facade.Location != path) throw new Exception("Source facade IO identity/end");
            Console.WriteLine("PASS exact source NET462 IO facade resolves five types across original mscorlib/System scopes and executes MemoryStream write/read on source NET8");
        }
        finally { context.Unload(); }
    }
}
