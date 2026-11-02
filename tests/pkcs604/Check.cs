using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Resources;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Security.Cryptography.Pkcs;
using System.Security.Cryptography.X509Certificates;
using System.Text;

internal static class Program
{
    static void Require(bool ok, string message) { if (!ok) throw new Exception(message); }
    static void Throws<T>(Action action) where T : Exception
    { try { action(); } catch (T) { return; } throw new Exception("Expected " + typeof(T).Name); }
    static int Main(string[] args)
    {
        string path = Path.GetFullPath(args[0]);
        var context = new AssemblyLoadContext("produced-pkcs604", isCollectible: true);
        string dependency = args.Length > 3 ? Path.GetFullPath(args[3]) : "";
        if (dependency.Length != 0) context.LoadFromAssemblyPath(dependency);
        context.LoadFromAssemblyPath(path);
        context.LoadFromAssemblyPath(typeof(Program).Assembly.Location).GetType("Program")!
            .GetMethod("Run", BindingFlags.Static | BindingFlags.NonPublic)!.Invoke(null, new object[] { path, args[1], args[2], dependency });
        return 0;
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static void Run(string path, string expectedResources, string pssVector, string dependency)
    {
        var assembly = typeof(SignedCms).Assembly;
        Require(assembly.Location == path, "execute exact produced Pkcs assembly");
        Require(assembly.GetName().Version!.ToString() == "6.0.0.0", "original assembly version");
        Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant() == "b03f5f7f11d50a3a", "original Microsoft key");
        Require(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>()!.Version == "6.0.1923.31806", "original release file version");
        Require(assembly.GetCustomAttribute<System.Runtime.Versioning.TargetFrameworkAttribute>()!.FrameworkName == ".NETCoreApp,Version=v6.0", "original NET6 framework");
        Require(!assembly.GetReferencedAssemblies().Any(a => a.Version!.Major >= 8), "no NET8/NET10 producer reference replacement");
        if (dependency.Length != 0)
            Require(typeof(System.Formats.Asn1.AsnWriter).Assembly.Location == dependency, "execute exact cached source ASN.1 dependency");
        byte[] data = Encoding.UTF8.GetBytes("Grüße 世界 original PKCS6 source \0");
        using var key = RSA.Create(2048);
        var request = new CertificateRequest("CN=Owned PKCS6 source test", key, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        using var cert = request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-1), DateTimeOffset.UtcNow.AddHours(1));
        foreach (bool detached in new[] { false, true })
        {
            var cms = new SignedCms(new ContentInfo(data), detached);
            var signer = new CmsSigner(SubjectIdentifierType.IssuerAndSerialNumber, cert) { DigestAlgorithm = new Oid("2.16.840.1.101.3.4.2.1"), IncludeOption = X509IncludeOption.EndCertOnly };
            cms.ComputeSignature(signer, true);
            byte[] encoded = cms.Encode();
            var decoded = detached ? new SignedCms(new ContentInfo(data), true) : new SignedCms();
            decoded.Decode(encoded);
            decoded.CheckSignature(true);
            Require(decoded.ContentInfo.Content.SequenceEqual(data) && decoded.SignerInfos.Count == 1, "CMS round trip");
            encoded[encoded.Length - 1] ^= 1;
            Throws<CryptographicException>(() => { var bad = detached ? new SignedCms(new ContentInfo(data), true) : new SignedCms(); bad.Decode(encoded); bad.CheckSignature(true); });
        }
        var pss = new SignedCms();
        pss.Decode(File.ReadAllBytes(pssVector));
        Require(pss.Version == 3 && pss.SignerInfos.Count == 1 && Encoding.ASCII.GetString(pss.ContentInfo.Content) == "This is a test\r\n", "original RSA-PSS signed document");
        // The original upstream vector deliberately has a 95-byte salt with
        // SHA256. NET6's original test requires this unsupported parameter error.
        bool rejectedPss = false;
        try { pss.CheckSignature(true); }
        catch (CryptographicException error)
        { rejectedPss = error.Message.Contains("95") && error.Message.Contains("SHA256"); }
        Require(rejectedPss, "original unsupported RSA-PSS salt rejection");
        var envelope = new EnvelopedCms(new ContentInfo(data), new AlgorithmIdentifier(new Oid("2.16.840.1.101.3.4.1.42")));
        envelope.Encrypt(new CmsRecipient(SubjectIdentifierType.IssuerAndSerialNumber, cert));
        byte[] encrypted = envelope.Encode();
        var opened = new EnvelopedCms();
        opened.Decode(encrypted);
        opened.Decrypt(new X509Certificate2Collection(cert));
        Require(opened.ContentInfo.Content.SequenceEqual(data), "CMS AES256 decryption");
        using var wrongKey = RSA.Create(2048);
        using var wrongCert = new CertificateRequest("CN=Wrong owned key", wrongKey, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1)
            .CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-1), DateTimeOffset.UtcNow.AddHours(1));
        Throws<CryptographicException>(() => { var wrong = new EnvelopedCms(); wrong.Decode(encrypted); wrong.Decrypt(new X509Certificate2Collection(wrongCert)); });
        var safe = new Pkcs12SafeContents();
        safe.AddCertificate(cert);
        var pbe = new PbeParameters(PbeEncryptionAlgorithm.Aes256Cbc, HashAlgorithmName.SHA256, 1000);
        safe.AddShroudedKey(key, "owned password", pbe);
        var pfxBuilder = new Pkcs12Builder();
        pfxBuilder.AddSafeContentsEncrypted(safe, "owned password", pbe);
        pfxBuilder.SealWithMac("owned password", HashAlgorithmName.SHA256, 1000);
        byte[] pfx = pfxBuilder.Encode();
        var info = Pkcs12Info.Decode(pfx, out int read, true);
        Require(read == pfx.Length && info.VerifyMac("owned password") && !info.VerifyMac("wrong password"), "PKCS12 MAC/password validation");
        info.AuthenticatedSafe[0].Decrypt("owned password");
        Require(info.AuthenticatedSafe[0].GetBags().OfType<Pkcs12CertBag>().Count() == 1, "PKCS12 safe contents");
        Require(info.AuthenticatedSafe[0].GetBags().OfType<Pkcs12ShroudedKeyBag>().Count() == 1, "PKCS12 private key bag");
        byte[] digest = SHA256.HashData(data);
        byte[] nonce = new byte[] { 1, 2, 3, 4 };
        var timestampRequest = Rfc3161TimestampRequest.CreateFromHash(digest, HashAlgorithmName.SHA256, nonce: nonce, requestSignerCertificates: true);
        byte[] encodedRequest = timestampRequest.Encode();
        Require(Rfc3161TimestampRequest.TryDecode(encodedRequest, out var decodedRequest, out int consumed) && consumed == encodedRequest.Length,
            "RFC3161 request decode");
        Require(decodedRequest!.GetMessageHash().Span.SequenceEqual(digest) && decodedRequest.GetNonce()!.Value.Span.SequenceEqual(nonce), "RFC3161 hash/nonce");
        Throws<CryptographicException>(() => new SignedCms().Decode(new byte[] { 1, 2, 3 }));
        var expected = System.Text.Json.JsonSerializer.Deserialize<System.Collections.Generic.Dictionary<string, string>>(File.ReadAllText(expectedResources))!;
        using (var stream = assembly.GetManifestResourceStream("FxResources.System.Security.Cryptography.Pkcs.SR.resources")!)
        using (var reader = new ResourceReader(stream))
        {
            int count = 0;
            foreach (DictionaryEntry item in reader) { Require(expected[(string)item.Key] == (string)item.Value!, "original resource value"); count++; }
            Require(count == expected.Count && count > 0, "complete neutral resource set");
        }
        using (var pe = new PEReader(File.OpenRead(path)))
        using (var pdb = MetadataReaderProvider.FromPortablePdbStream(File.OpenRead(Path.ChangeExtension(path, ".pdb"))))
        {
            var cv = pe.ReadCodeViewDebugDirectoryData(pe.ReadDebugDirectory().Single(e => e.Type == DebugDirectoryEntryType.CodeView));
            Require(cv.Guid == new Guid(pdb.GetMetadataReader().DebugMetadataHeader!.Id.Take(16).ToArray()), "portable PDB association");
        }
        GC.Collect(); GC.WaitForPendingFinalizers();
        Console.WriteLine("PASS produced original NET6 PKCS6: attached/detached CMS RSA, original unsupported PSS salt rejection, tamper rejection, AES envelope/decryption/wrong key, PKCS12/password/MAC, resources and PDB; host=" + RuntimeInformation.FrameworkDescription);
    }
}
