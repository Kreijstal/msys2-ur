using System;
using System.IO;
using System.Reflection;
using System.Resources;
using System.Runtime.Loader;
using System.Runtime.Versioning;
using System.Globalization;
using System.Text.Json;
using System.Xml;
using System.Xml.Linq;

class ResourceCheck
{
    static void Main(string[] args)
    {
        AssemblyLoadContext.Default.Resolving += (c,n) => { string p=Path.Combine(args[3],n.Name+".dll"); return File.Exists(p)?c.LoadFromAssemblyPath(p):null; };
        var a=AssemblyLoadContext.Default.LoadFromAssemblyPath(args[0]);
        if(a.GetName().Version.ToString()!="5.3.0.0" || Convert.ToHexString(a.GetName().GetPublicKeyToken()).ToLowerInvariant()!="31bf3856ad364e35")throw new Exception("task identity");
        if(a.GetCustomAttribute<TargetFrameworkAttribute>().FrameworkName!=".NETCoreApp,Version=v10.0")throw new Exception("original task framework");
        foreach(var name in new[]{"Csc","Vbc","CopyRefAssembly","GenerateMSBuildEditorConfig","MapSourceRoots"})
            if(a.GetType("Microsoft.CodeAnalysis.BuildTasks."+name)==null)throw new Exception("task type "+name);
        using var xml=new XmlTextReader(args[1]);xml.WhitespaceHandling=WhitespaceHandling.All;
        var doc=XDocument.Load(xml,LoadOptions.PreserveWhitespace);
        using var neutral=new ResourceSet(a.GetManifestResourceStream("Microsoft.CodeAnalysis.BuildTasks.ErrorString.resources"));
        int count=0;
        foreach(var item in doc.Root.Elements("data")) {
            if(neutral.GetString(item.Attribute("name").Value)!=item.Element("value").Value)throw new Exception("neutral string");
            count++;
        }
        using var expected=JsonDocument.Parse(File.ReadAllText(args[2]));
        foreach(var item in expected.RootElement.EnumerateArray()) {
            var culture=CultureInfo.GetCultureInfo(item.GetProperty("culture").GetString());
            var satellite=a.GetSatelliteAssembly(culture);
            if(satellite.GetName().Version.ToString()!="5.3.0.0" || Convert.ToHexString(satellite.GetName().GetPublicKeyToken()).ToLowerInvariant()!="31bf3856ad364e35")throw new Exception("satellite identity");
            using var set=new ResourceSet(satellite.GetManifestResourceStream("Microsoft.CodeAnalysis.BuildTasks.ErrorString."+culture.Name+".resources"));
            var rm=new ResourceManager("Microsoft.CodeAnalysis.BuildTasks.ErrorString",a);
            foreach(var value in item.GetProperty("strings").EnumerateObject()) {
                if(set.GetString(value.Name)!=value.Value.GetString() || rm.GetString(value.Name,culture)!=value.Value.GetString())throw new Exception(culture+"/"+value.Name);
                count++;
            }
        }
        Console.WriteLine("PASS original NET10 task identity,five task types and "+count+" exact neutral/localized resource values");
    }
}
