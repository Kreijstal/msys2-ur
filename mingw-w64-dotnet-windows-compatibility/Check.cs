using System;
using System.Collections.Generic;
using System.CodeDom;
using System.CodeDom.Compiler;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Management;
using System.Reflection;
using System.Runtime.Caching;
using System.Text;
using System.Text.Json;

Console.WriteLine("Runtime: " + Environment.Version);
using var groups = JsonDocument.Parse(File.ReadAllText(args[0]));
foreach (var dependency in groups.RootElement.GetProperty("net8.0").EnumerateObject())
{
    var assembly = Assembly.Load(new AssemblyName(dependency.Name));
    var exported = assembly.GetExportedTypes();
    Console.WriteLine("LOAD " + dependency.Name + " " + assembly.GetName().Version + " types=" + exported.Length);
}
using (var cache = new MemoryCache("owned-source-compat-" + Guid.NewGuid()))
{
    cache.Add("answer", 42, DateTimeOffset.UtcNow.AddMinutes(1));
    if (!Equals(cache.Get("answer"), 42)) throw new Exception("Source cache");
}
using (var bitmap = new Bitmap(2, 2))
{
    bitmap.SetPixel(1, 1, Color.CornflowerBlue);
    if (bitmap.GetPixel(1, 1).ToArgb() != Color.CornflowerBlue.ToArgb()) throw new Exception("Source GDI+");
}
using (var search = new ManagementObjectSearcher("SELECT BuildNumber FROM Win32_OperatingSystem"))
using (var rows = search.Get())
{
    var found = new List<string>();
    foreach (ManagementObject row in rows) using (row) found.Add((string)row["BuildNumber"]);
    if (found.Count != 1 || found[0] != Environment.OSVersion.Version.Build.ToString()) throw new Exception("Source WMI");
}
Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
if (Encoding.GetEncoding(1252).GetString(new byte[] { 0x80 }) != "€") throw new Exception("Code pages");
using (var provider = CodeDomProvider.CreateProvider("CSharp"))
using (var writer = new StringWriter())
{
    provider.GenerateCodeFromExpression(new CodePrimitiveExpression(42), writer, new CodeGeneratorOptions());
    if (!writer.ToString().Contains("42")) throw new Exception("CodeDom");
}
var sql = new System.Data.SqlClient.SqlConnectionStringBuilder("Server=localhost;Database=Owned;Integrated Security=true");
if (sql.InitialCatalog != "Owned") throw new Exception("SqlClient package");
_ = new System.ServiceModel.BasicHttpBinding();
_ = new System.ServiceModel.NetTcpBinding();
_ = new System.ServiceModel.Syndication.SyndicationFeed("owned", "source", null);
foreach (System.Diagnostics.ProcessModule module in System.Diagnostics.Process.GetCurrentProcess().Modules)
    if (module.FileName.Replace('\\', '/').Contains("/Microsoft.NET/Framework", StringComparison.OrdinalIgnoreCase))
        throw new Exception("Framework fallback: " + module.FileName);
Console.WriteLine("PASS whole metapackage dependency load, owned cache/bitmap, local WMI, codepages/CodeDom, SQL metadata and WCF/Syndication; no Framework fallback");
