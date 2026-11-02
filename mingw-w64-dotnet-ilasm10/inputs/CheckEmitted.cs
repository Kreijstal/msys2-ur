using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;

static class Program
{
    static int Main(string[] args)
    {
        using var pe=new PEReader(File.OpenRead(args[0]));var md=pe.GetMetadataReader();var a=md.GetAssemblyDefinition();
        if(md.GetString(a.Name)!="System.Runtime.CompilerServices.Unsafe" || a.Version!=new Version(6,0,0,0))throw new Exception("Original Unsafe identity");
        string token=Convert.ToHexString(SHA1.HashData(md.GetBlobBytes(a.PublicKey)).TakeLast(8).Reverse().ToArray()).ToLowerInvariant();
        if(token!="b03f5f7f11d50a3a")throw new Exception("Original Unsafe key");
        var type=md.TypeDefinitions.Select(md.GetTypeDefinition).Single(t=>md.GetString(t.Name)=="Unsafe");
        int count=type.GetMethods().Select(md.GetMethodDefinition).Count(m=>(m.Attributes&MethodAttributes.MemberAccessMask)==MethodAttributes.Public && (m.Attributes&MethodAttributes.Static)!=0);
        if(count!=42)throw new Exception("Original Unsafe public methods: "+count);
        using var stream=File.OpenRead(Path.ChangeExtension(args[0],".pdb"));
        using var pdb=MetadataReaderProvider.FromPortablePdbStream(stream);
        if(pdb.GetMetadataReader().Documents.Count==0)throw new Exception("Missing original IL portable PDB documents");
        if(!pe.ReadDebugDirectory().Any(e=>e.Type==DebugDirectoryEntryType.CodeView))throw new Exception("Missing PE debug directory");
        Console.WriteLine("PASS original Unsafe IL identity, key, 42 public methods and emitted portable PDB");
        return 0;
    }
}
