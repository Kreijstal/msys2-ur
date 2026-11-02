using System;
using System.Linq;
using System.Resources;
using System.Xml.Linq;

static class WriteResources
{
    static void Main(string[] args)
    {
        var document = XDocument.Load(args[0]);
        using var writer = new ResourceWriter(args[1]);
        int count = 0;
        foreach (var node in document.Root!.Elements("data"))
        {
            if (node.Attribute("type") != null || node.Attribute("mimetype") != null) throw new Exception("Review non-string resource");
            writer.AddResource(node.Attribute("name")!.Value, node.Element("value")!.Value); count++;
        }
        writer.Generate(); Console.WriteLine("PASS resources generated from original source resx: " + count);
    }
}
