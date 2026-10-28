using System;
using System.Collections;
using System.Data.SqlClient;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Security.Cryptography;
using System.Text.Json;

static class CheckAssets
{
    static void Require(bool value,string message) { if(!value)throw new Exception(message); }
    static string Hash(byte[] bytes)=>Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
    static int Main(string[] args)
    {
        using var expected=JsonDocument.Parse(File.ReadAllText(args[0]));var root=expected.RootElement;
        var assembly=typeof(SqlConnection).Assembly;
        Require(assembly.GetName().Version.ToString()=="4.6.1.6","original assembly version");
        Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()=="b03f5f7f11d50a3a","original public-signing identity");
        Require(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>().Version=="4.9.1.0","original file version");
        Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion=="4.9.1+84b081710c66cc560b77d4de38cee493c3a38e9d","exact informational source commit");
        Require(Hash(File.ReadAllBytes(assembly.Location))==root.GetProperty("implementation_sha256").GetString(),"executing exact source Windows implementation");
        var factory=assembly.GetType("System.Data.SqlClient.TdsParserStateObjectFactory",true);
        Require((bool)factory.GetProperty("UseManagedSNI",BindingFlags.Public|BindingFlags.Static).GetValue(null),"Release uses original managed SNI source");
        using(var stream=assembly.GetManifestResourceStream(root.GetProperty("resource_name").GetString()))
        using(var reader=new ResourceReader(stream))
        {
            var actual=reader.Cast<DictionaryEntry>().ToDictionary(e=>(string)e.Key,e=>(string)e.Value);
            var strings=root.GetProperty("resource_strings");Require(actual.Count==strings.EnumerateObject().Count(),"exact resource count");
            foreach(var item in strings.EnumerateObject())Require(actual[item.Name]==item.Value.GetString(),"original resource "+item.Name);
        }
        using(var stream=assembly.GetManifestResourceStream(root.GetProperty("metadata_resource_name").GetString()))
        using(var bytes=new MemoryStream()) {stream.CopyTo(bytes);Require(Hash(bytes.ToArray())==root.GetProperty("metadata_resource_sha256").GetString(),"original SQL metadata XML bytes");}
        foreach(ProcessModule module in Process.GetCurrentProcess().Modules)
            Require(!module.ModuleName.Equals("sni.dll",StringComparison.OrdinalIgnoreCase) && !module.FileName.Contains(@"\Microsoft.NET\Framework",StringComparison.OrdinalIgnoreCase),"no proprietary SNI or Framework implementation");
        Console.WriteLine("PASS experimental source SqlClient exact selected runtime/hash/identity, Release managed SNI, all original resource strings and metadata XML; location="+assembly.Location);
        return 0;
    }
}
