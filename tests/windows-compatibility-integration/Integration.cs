using System;
using System.CodeDom;
using System.CodeDom.Compiler;
using System.Collections.Generic;
using System.ComponentModel.Composition.Hosting;
using System.ComponentModel.Composition.Registration;
using System.Configuration;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.IO.Packaging;
using System.Linq;
using System.Reflection;
using System.Reflection.Context;
using System.Runtime.Caching;
using System.Security.Cryptography;
using System.Security.Cryptography.Pkcs;
using System.Security.Cryptography.X509Certificates;
using System.Security.Cryptography.Xml;
using System.ServiceModel.Syndication;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Xml;

public interface IDocumentTitle { string Value { get; } }
public sealed class DocumentTitle : IDocumentTitle { public string Value => "source € 雪 <&>"; }
sealed class DocumentProjection : CustomReflectionContext
{
    protected override IEnumerable<PropertyInfo> AddProperties(Type type)
    {
        if (type == typeof(DocumentTitle))
            yield return CreateProperty(MapType(typeof(string).GetTypeInfo()).AsType(), "Origin", _ => "source-feed", null);
    }
}

public static class CompatibilityIntegration
{
    static void Require(bool condition, string message, List<string> checks)
    {
        if (!condition) throw new Exception(message);
        checks.Add(message);
    }

    public static string Run(string root, string graphFile)
    {
        Directory.CreateDirectory(root);
        var checks = new List<string>();
        using var graph = JsonDocument.Parse(File.ReadAllText(graphFile));
        var dependencies = graph.RootElement.GetProperty("net8.0").EnumerateObject().Select(p => p.Name).ToArray();
        Require(dependencies.Length == 35, "Original metapackage has 35 direct dependencies", checks);
        foreach (string dependency in dependencies)
        {
            var loaded = Assembly.Load(new AssemblyName(dependency));
            int exported = loaded.GetExportedTypes().Length;
            Require(loaded.GetName().Name == dependency,
                "Loaded exported types: " + dependency + " (" + exported + ")", checks);
        }

        var registration = new RegistrationBuilder();
        registration.ForType<DocumentTitle>().Export<IDocumentTitle>();
        using var catalog = new TypeCatalog(new[] { typeof(DocumentTitle) }, registration);
        using var composition = new CompositionContainer(catalog);
        string title = composition.GetExportedValue<IDocumentTitle>().Value;
        var projection = new DocumentProjection().MapType(typeof(DocumentTitle).GetTypeInfo());
        Require((string)projection.GetProperty("Origin").GetValue(new DocumentTitle()) == "source-feed",
            "Convention composition and custom reflection agree", checks);
        Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
        Require(Encoding.GetEncoding(1252).GetString(new byte[] { 0x80 }) == "€", "Codepages preserves euro sign", checks);
        using var codeDom = CodeDomProvider.CreateProvider("CSharp");
        using var generated = new StringWriter();
        codeDom.GenerateCodeFromExpression(new CodePrimitiveExpression(title), generated, new CodeGeneratorOptions());
        Require(generated.ToString().Contains("source"), "Composed title reaches CodeDom", checks);

        using var key = RSA.Create(2048);
        var request = new CertificateRequest("CN=Owned compatibility integration", key,
            HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        using var certificate = request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-1), DateTimeOffset.UtcNow.AddHours(1));
        using var cache = new MemoryCache("owned-compatibility-" + Guid.NewGuid());
        var payloads = new[] { title, "empty:", "line1\nline2 😀" };
        for (int iteration = 0; iteration < payloads.Length; iteration++)
        {
            string payload = payloads[iteration];
            var feed = new SyndicationFeed(title, payload, new Uri("urn:owned:compatibility")) { Id = "urn:owned:" + iteration };
            using var feedText = new StringWriter();
            using (var writer = XmlWriter.Create(feedText, new XmlWriterSettings {
                OmitXmlDeclaration = true, NewLineHandling = NewLineHandling.Entitize }))
                feed.SaveAsAtom10(writer);
            var document = new XmlDocument { PreserveWhitespace = true };
            document.LoadXml(feedText.ToString());
            var signed = new SignedXml(document) { SigningKey = key };
            signed.SignedInfo.SignatureMethod = SignedXml.XmlDsigRSASHA256Url;
            var reference = new Reference("") { DigestMethod = SignedXml.XmlDsigSHA256Url };
            reference.AddTransform(new XmlDsigEnvelopedSignatureTransform());
            signed.AddReference(reference);
            signed.ComputeSignature();
            document.DocumentElement.AppendChild(document.ImportNode(signed.GetXml(), true));
            byte[] image;
            using (var bitmap = new Bitmap(2, 2))
            using (var png = new MemoryStream())
            {
                bitmap.SetPixel(1, 1, Color.CornflowerBlue);
                bitmap.Save(png, ImageFormat.Png);
                image = png.ToArray();
            }
            var documentUri = new Uri("/document.xml", UriKind.Relative);
            var imageUri = new Uri("/preview.png", UriKind.Relative);
            byte[] packageBytes;
            using (var stream = new MemoryStream())
            {
                using (var package = Package.Open(stream, FileMode.Create, FileAccess.ReadWrite))
                {
                    using (var part = package.CreatePart(documentUri, "application/atom+xml", CompressionOption.Normal).GetStream())
                    {
                        byte[] xml = Encoding.UTF8.GetBytes(document.OuterXml);
                        part.Write(xml, 0, xml.Length);
                    }
                    using (var part = package.CreatePart(imageUri, "image/png", CompressionOption.Normal).GetStream())
                        part.Write(image, 0, image.Length);
                    package.CreateRelationship(documentUri, TargetMode.Internal, "urn:owned:document");
                }
                packageBytes = stream.ToArray();
            }
            var cms = new EnvelopedCms(new ContentInfo(packageBytes),
                new AlgorithmIdentifier(new Oid("2.16.840.1.101.3.4.1.42")));
            cms.Encrypt(new CmsRecipient(certificate));
            byte[] entropy = RandomNumberGenerator.GetBytes(32);
            byte[] encrypted = ProtectedData.Protect(cms.Encode(), entropy, DataProtectionScope.CurrentUser);
            string configPath = Path.Combine(root, "document-" + iteration + ".config");
            var mapping = new ExeConfigurationFileMap { ExeConfigFilename = configPath };
            var config = ConfigurationManager.OpenMappedExeConfiguration(mapping, ConfigurationUserLevel.None);
            config.AppSettings.Settings.Add("payload", Convert.ToBase64String(encrypted));
            config.AppSettings.Settings.Add("source", generated.ToString());
            config.Save(ConfigurationSaveMode.Full);
            var reopened = ConfigurationManager.OpenMappedExeConfiguration(mapping, ConfigurationUserLevel.None);
            Require(reopened.AppSettings.Settings["source"].Value == generated.ToString(), "CodeDom/configuration Unicode roundtrip " + iteration, checks);
            encrypted = Convert.FromBase64String(reopened.AppSettings.Settings["payload"].Value);
            byte[] decoded = ProtectedData.Unprotect(encrypted, entropy, DataProtectionScope.CurrentUser);
            bool rejected = false;
            try { _ = ProtectedData.Unprotect(encrypted, new byte[32], DataProtectionScope.CurrentUser); }
            catch (CryptographicException) { rejected = true; }
            Require(rejected, "DPAPI rejects wrong entropy " + iteration, checks);
            var opened = new EnvelopedCms();
            opened.Decode(decoded);
            opened.Decrypt(new X509Certificate2Collection(certificate));
            Require(opened.ContentInfo.Content.SequenceEqual(packageBytes), "DPAPI/config/CMS restores package bytes " + iteration, checks);
            using var receivedStream = new MemoryStream(opened.ContentInfo.Content);
            using var received = Package.Open(receivedStream, FileMode.Open, FileAccess.Read);
            Require(received.GetRelationshipsByType("urn:owned:document").Single().TargetUri == documentUri,
                "OPC relationship preserved " + iteration, checks);
            var restored = new XmlDocument { PreserveWhitespace = true };
            using (var xml = received.GetPart(documentUri).GetStream()) restored.Load(xml);
            var signature = new SignedXml(restored);
            signature.LoadXml((XmlElement)restored.GetElementsByTagName("Signature", SignedXml.XmlDsigNamespaceUrl)[0]);
            Require(signature.CheckSignature(key), "Signed XML survives OPC/CMS/DPAPI/config " + iteration, checks);
            using (var reader = new XmlNodeReader(restored))
            {
                var parsed = SyndicationFeed.Load(reader);
                Require(parsed.Title.Text == title && parsed.Description.Text == payload,
                    "Syndication payload survives full pipeline " + iteration + ": " +
                    JsonSerializer.Serialize(new { expected = payload, actual = parsed.Description.Text }), checks);
            }
            using (var png = received.GetPart(imageUri).GetStream())
            using (var bitmap = new Bitmap(png))
                Require(bitmap.GetPixel(1, 1).ToArgb() == Color.CornflowerBlue.ToArgb(), "GDI+ PNG survives full pipeline " + iteration, checks);
            restored.DocumentElement.SetAttribute("tampered", "yes");
            Require(!signature.CheckSignature(key), "XML tampering rejected after full pipeline " + iteration, checks);
            bool removed = false;
            cache.Set("document", payload, new CacheItemPolicy {
                RemovedCallback = args => removed = args.RemovedReason == CacheEntryRemovedReason.Removed });
            Require((string)cache.Get("document") == payload, "Restored document enters cache " + iteration, checks);
            cache.Remove("document");
            Require(removed && cache.Get("document") == null, "Cache removal callback and cleanup " + iteration, checks);
            GC.Collect(2, GCCollectionMode.Forced, true, true);
        }
        string[] exercised = { "System.CodeDom", "System.ComponentModel.Composition", "System.ComponentModel.Composition.Registration",
            "System.Configuration.ConfigurationManager", "System.Drawing.Common", "System.IO.Packaging", "System.Reflection.Context",
            "System.Runtime.Caching", "System.Security.Cryptography.Pkcs", "System.Security.Cryptography.ProtectedData",
            "System.Security.Cryptography.Xml", "System.ServiceModel.Syndication", "System.Text.Encoding.CodePages" };
        var assemblies = dependencies.Concat(new[] { "System.Windows.Extensions" }).Distinct().Select(name => {
            var assembly = Assembly.Load(new AssemblyName(name));
            return new { name, identity = assembly.FullName, path = assembly.Location,
                sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(assembly.Location))).ToLowerInvariant() };
        }).ToArray();
        foreach (System.Diagnostics.ProcessModule module in System.Diagnostics.Process.GetCurrentProcess().Modules)
            if (module.FileName.Replace('\\', '/').Contains("/Microsoft.NET/Framework", StringComparison.OrdinalIgnoreCase))
                throw new Exception("Framework implementation loaded: " + module.FileName);
        return JsonSerializer.Serialize(new { runtime = Environment.Version.ToString(),
            apartment = Thread.CurrentThread.GetApartmentState().ToString(), checks, assertions = checks.Count,
            dependency_ids_loaded = dependencies.Length, cross_library_behavior_ids = exercised,
            assemblies, provider_connection_attempted = false, full_dependency_goal_complete = false },
            new JsonSerializerOptions { WriteIndented = true });
    }

    public static int Main(string[] args)
    {
        string json = Run(args[0], args[1]);
        File.WriteAllText(args[2], json);
        Console.WriteLine("PASS cross-library compatibility pipeline: " + JsonDocument.Parse(json).RootElement.GetProperty("assertions").GetInt32() + " assertions");
        return 0;
    }
}
