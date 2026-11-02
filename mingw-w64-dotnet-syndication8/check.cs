using System;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.ServiceModel.Syndication;
using System.Text.Json;
using System.Xml;

static class Check
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static void Main(string[] args)
    {
        var assembly=typeof(SyndicationFeed).Assembly;
        Require(assembly.GetName().Version==new Version(8,0,0,0),"assembly version");
        Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()=="cc7b13ffcd2ddd51","public identity");
        Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion.StartsWith("8.0.0+runtime-v8.0.31"),"source version");
        Require(Path.GetDirectoryName(assembly.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"consumer-local implementation");
        var date=new DateTimeOffset(2026,10,26,9,12,34,TimeSpan.Zero);
        var feed=new SyndicationFeed("Feed λ 日本語","description",new Uri("https://example.org/")){LastUpdatedTime=date};
        var item=new SyndicationItem("Entry λ","body",new Uri("https://example.org/item")){PublishDate=date,LastUpdatedTime=date};
        item.ElementExtensions.Add("custom","urn:fixture","extension λ");
        feed.Items=new[]{item};
        foreach(bool atom in new[]{true,false})
        {
            using var stream=new MemoryStream();
            using(var writer=XmlWriter.Create(stream,new XmlWriterSettings{CloseOutput=false}))
            {if(atom)feed.SaveAsAtom10(writer);else feed.SaveAsRss20(writer);}
            stream.Position=0;
            using var reader=XmlReader.Create(stream);
            var loaded=SyndicationFeed.Load(reader);var entry=loaded.Items.Single();
            Require(loaded.Title.Text==feed.Title.Text && entry.Title.Text==item.Title.Text,"Unicode feed/item roundtrip");
            Require(entry.PublishDate==date && entry.Links.Any(l=>l.Uri==item.Links[0].Uri),"date/link roundtrip");
            Require(entry.ElementExtensions.ReadElementExtensions<string>("custom","urn:fixture").Single()=="extension λ","extension roundtrip");
        }
        var service=new ServiceDocument();
        var workspace=new Workspace{Title=new TextSyndicationContent("Workspace λ")};
        workspace.Collections.Add(new ResourceCollectionInfo("Posts",new Uri("https://example.org/posts")));
        service.Workspaces.Add(workspace);
        using(var stream=new MemoryStream())
        {
            using(var writer=XmlWriter.Create(stream,new XmlWriterSettings{CloseOutput=false}))service.Save(writer);
            stream.Position=0;using var reader=XmlReader.Create(stream);
            var loaded=ServiceDocument.Load(reader);
            Require(loaded.Workspaces.Single().Title.Text=="Workspace λ" && loaded.Workspaces.Single().Collections.Single().Link==new Uri("https://example.org/posts"),"AtomPub roundtrip");
        }
        try
        {
            using var reader=XmlReader.Create(new StringReader("<invalid/>"));SyndicationFeed.Load(reader);
            throw new Exception("invalid feed accepted");
        }
        catch(XmlException error){Require(!string.IsNullOrWhiteSpace(error.Message),"error resources");}
        using var manifest=JsonDocument.Parse(File.ReadAllText(args[0]));
        int sets=0,strings=0;
        foreach(var entry in manifest.RootElement.EnumerateArray())
        {
            var culture=CultureInfo.GetCultureInfo(entry.GetProperty("culture").GetString());
            var satellite=culture.Name.Length==0?assembly:assembly.GetSatelliteAssembly(culture);
            string resource=entry.GetProperty("resource").GetString()+(culture.Name.Length==0?"":"."+culture.Name)+".resources";
            using var reader=new ResourceReader(satellite.GetManifestResourceStream(resource)??throw new Exception(resource));
            var actual=reader.Cast<System.Collections.DictionaryEntry>().ToDictionary(e=>(string)e.Key,e=>(string)e.Value);
            foreach(var pair in entry.GetProperty("strings").EnumerateObject())
            {Require(actual.TryGetValue(pair.Name,out var value)&&value==pair.Value.GetString(),"localized string "+culture.Name+"/"+pair.Name);strings++;}
            Require(actual.Count==entry.GetProperty("strings").EnumerateObject().Count(),"localized resource count");sets++;
        }
        Require(sets==manifest.RootElement.GetArrayLength() && sets>0,"all upstream resource sets");
        Console.WriteLine($"PASS Syndication 8: Atom/RSS Unicode, dates, links, extensions, AtomPub, invalid XML; {sets} resource sets/{strings} strings; identity/source/location");
    }
}
