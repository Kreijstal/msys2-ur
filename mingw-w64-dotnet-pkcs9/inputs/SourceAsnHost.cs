using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Text.Json;
using System.Collections.Generic;
using System.Runtime.Loader;

sealed class SourceContext : AssemblyLoadContext
{
    readonly string directory,asn;
    public SourceContext(string directory,string asn):base("exact-source-asn9",true){this.directory=directory;this.asn=asn;}
    protected override Assembly? Load(AssemblyName name)
    {
        if(name.Name=="System.Formats.Asn1")return LoadFromAssemblyPath(asn);
        if(name.Name=="System.Security.Cryptography.Pkcs")return LoadFromAssemblyPath(Path.Combine(directory,name.Name+".dll"));
        return null;
    }
}

static class SourceAsnHost
{
    static int Main(string[] args)
    {
        try
        {
            string directory=Path.GetFullPath(args[0]),asn=Path.GetFullPath(args[1]);
            var context=new SourceContext(directory,asn);
            var fixture=context.LoadFromAssemblyPath(Path.Combine(directory,"Probe.dll"));
            int result=(int)fixture.EntryPoint!.Invoke(null,new object[]{new[]{directory}})!;
            var loaded=context.Assemblies.Single(a=>a.GetName().Name=="System.Formats.Asn1");
            if(Path.GetFullPath(loaded.Location)!=asn||loaded.GetName().Version!=new Version(9,0,0,0))throw new Exception("Exact source ASN9 dependency was not executed");
            var strings=JsonSerializer.Deserialize<Dictionary<string,string>>(File.ReadAllText(Path.Combine(Path.GetDirectoryName(asn)!,"neutral-strings.json")))!;
            var resources=new ResourceManager("FxResources.System.Formats.Asn1.SR",loaded);
            if(strings.Count!=34)throw new Exception("Original ASN.1 resource inventory");
            foreach(var pair in strings)if(resources.GetString(pair.Key,System.Globalization.CultureInfo.InvariantCulture)!=pair.Value)throw new Exception("Original ASN.1 resource "+pair.Key);
            Console.WriteLine("PASS all34 original source ASN.1 resource values");
            Console.WriteLine("PASS original source NET9 ASN dependency executed: "+loaded.FullName);
            context.Unload();return result;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
}
