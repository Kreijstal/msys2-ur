using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Resources;
using System.Runtime.Loader;
using System.Text.Json;

internal static class Program
{
    static void Require(bool condition, string message) { if (!condition) throw new Exception(message); }
    static int Main(string[] args)
    {
        string bin=Path.GetFullPath(args[0]);
        AssemblyLoadContext.Default.Resolving += (_,name) => File.Exists(Path.Combine(bin,name.Name+".dll")) ? AssemblyLoadContext.Default.LoadFromAssemblyPath(Path.Combine(bin,name.Name+".dll")) : null;
        var models=JsonDocument.Parse(File.ReadAllText(args[1])).RootElement;
        var records=JsonDocument.Parse(File.ReadAllText(args[2])).RootElement.GetProperty("projects");
        int sets=0,values=0,satellites=0,pdbs=0;
        foreach(var record in records.EnumerateArray())
        {
            string name=record.GetProperty("assembly").GetString()!;
            var assembly=AssemblyLoadContext.Default.LoadFromAssemblyPath(Path.Combine(bin,name+".dll"));
            var identity=assembly.GetName();
            Require(identity.Version!.ToString()==record.GetProperty("assembly_version").GetString(),name+" assembly version");
            string token=Convert.ToHexString(identity.GetPublicKeyToken()!).ToLowerInvariant();
            Require(token==(record.GetProperty("key_policy").GetString()=="Open" ? "cc7b13ffcd2ddd51":record.GetProperty("key_policy").GetString()=="MicrosoftAspNetCore" ? "adb9793829ddae60":"31bf3856ad364e35"),name+" public key");
            Require(assembly.GetCustomAttribute<System.Runtime.Versioning.TargetFrameworkAttribute>()!.FrameworkName==(record.GetProperty("original_target").GetString()=="net10.0" ? ".NETCoreApp,Version=v10.0":".NETStandard,Version=v2.0"),name+" target framework");
            Require(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>()!.Version==record.GetProperty("file_version").GetString(),name+" file version");
            using(var peStream=File.OpenRead(Path.Combine(bin,name+".dll")))
            using(var pe=new PEReader(peStream))
            using(var pdbStream=File.OpenRead(Path.Combine(bin,name+".pdb")))
            using(var pdb=MetadataReaderProvider.FromPortablePdbStream(pdbStream))
            {
                var cv=pe.ReadDebugDirectory().Single(e=>e.Type==DebugDirectoryEntryType.CodeView);
                var id=pdb.GetMetadataReader().DebugMetadataHeader!.Id.ToArray();
                Require(pe.ReadCodeViewDebugDirectoryData(cv).Guid==new Guid(id.Take(16).ToArray()),name+" portable PDB GUID");
                Require(cv.Stamp==BitConverter.ToUInt32(id,16),name+" portable PDB stamp");pdbs++;
            }
            foreach(var model in models.EnumerateArray().Where(m=>m.GetProperty("assembly").GetString()==name))
            {
                string culture=model.GetProperty("culture").GetString()!, resource=model.GetProperty("resource").GetString()!;
                var selected=culture.Length==0 ? assembly:assembly.GetSatelliteAssembly(CultureInfo.GetCultureInfo(culture));
                var satName=selected.GetName();
                Require(satName.Version==identity.Version && (culture.Length==0 || satName.CultureName==culture),name+" satellite identity "+culture);
                Require(Convert.ToHexString(satName.GetPublicKeyToken()!)==Convert.ToHexString(identity.GetPublicKeyToken()!),name+" satellite key");
                string manifest=resource+(culture.Length==0 ? "":"."+culture)+".resources";
                using var stream=selected.GetManifestResourceStream(manifest) ?? throw new Exception("Missing "+name+"/"+manifest);
                using var reader=new ResourceReader(stream);
                var actual=reader.Cast<DictionaryEntry>().ToDictionary(p=>(string)p.Key,p=>(string)p.Value!);
                var expected=model.GetProperty("strings");
                Require(actual.Count==expected.EnumerateObject().Count(),name+" resource count "+manifest);
                var manager=new ResourceManager(resource,assembly);
                foreach(var item in expected.EnumerateObject())
                {
                    string text=item.Value.GetString()!;
                    Require(actual.TryGetValue(item.Name,out var value) && value==text,name+" raw value "+culture+"/"+item.Name+" expected="+JsonSerializer.Serialize(text)+" actual="+JsonSerializer.Serialize(value));
                    Require(manager.GetString(item.Name,culture.Length==0 ? CultureInfo.GetCultureInfo("en-US"):CultureInfo.GetCultureInfo(culture))==text,name+" manager value "+culture+"/"+item.Name);values++;
                }
                sets++;
            }
            satellites+=Directory.GetDirectories(bin).Count(folder=>File.Exists(Path.Combine(folder,name+".resources.dll")));
        }
        Require(sets==models.GetArrayLength() && pdbs==records.GetArrayLength(),"Complete logging resource/PDB coverage");
        Console.WriteLine($"PASS {sets} neutral/localized resource sets, {values} exact values, {satellites} satellite identities, original NET10/NS2 identities and portable PDBs");return 0;
    }
}
