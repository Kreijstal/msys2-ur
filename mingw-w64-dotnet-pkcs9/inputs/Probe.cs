using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Security.Cryptography;
using System.Security.Cryptography.Pkcs;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;

internal static class Probe
{
    static void Need(bool condition,string message){if(!condition)throw new Exception(message);}
    static void Throws(Action action,string message){try{action();}catch(CryptographicException){return;}throw new Exception(message);}
    static void Cms(string root,byte[] content,X509Certificate2 certificate,AsymmetricAlgorithm key,string name)
    {
        var signer=new CmsSigner(certificate){PrivateKey=key,DigestAlgorithm=new Oid("2.16.840.1.101.3.4.2.1"),IncludeOption=X509IncludeOption.EndCertOnly};
        signer.SignedAttributes.Add(new Pkcs9SigningTime(new DateTime(2026,1,2,3,4,5,DateTimeKind.Utc)));
        var signed=new SignedCms(new ContentInfo(content),false);signed.ComputeSignature(signer,true);
        var decoded=new SignedCms();decoded.Decode(signed.Encode());decoded.CheckSignature(true);
        Need(decoded.ContentInfo.Content.SequenceEqual(content)&&decoded.SignerInfos.Count==1,"Attached "+name);
        Need(decoded.SignerInfos[0].SignedAttributes.Count>=2,"Signed attributes");
        File.WriteAllBytes(Path.Combine(root,name+"-attached.cms"),signed.Encode());
        var corrupt=signed.Encode();corrupt[^1]^=1;Throws(()=>{var bad=new SignedCms();bad.Decode(corrupt);bad.CheckSignature(true);},"Corrupt signature accepted");
        var detached=new SignedCms(new ContentInfo(content),true);detached.ComputeSignature(signer,true);
        var detachedReader=new SignedCms(new ContentInfo(content),true);detachedReader.Decode(detached.Encode());detachedReader.CheckSignature(true);
        var wrong=content.ToArray();wrong[0]^=1;Throws(()=>{var bad=new SignedCms(new ContentInfo(wrong),true);bad.Decode(detached.Encode());bad.CheckSignature(true);},"Detached wrong content accepted");
        File.WriteAllBytes(Path.Combine(root,name+"-detached.cms"),detached.Encode());
        decoded.SignerInfos[0].ComputeCounterSignature(signer);Need(decoded.SignerInfos[0].CounterSignerInfos.Count==1,"Counter signature count");decoded.CheckSignature(true);decoded.SignerInfos[0].RemoveCounterSignature(0);
        var info=Pkcs8PrivateKeyInfo.Create(key);
        byte[] encrypted=info.Encrypt("owned-password",new PbeParameters(PbeEncryptionAlgorithm.Aes256Cbc,HashAlgorithmName.SHA256,1000));
        var restored=Pkcs8PrivateKeyInfo.DecryptAndDecode("owned-password",encrypted,out int read);
        Need(read==encrypted.Length&&restored.AlgorithmId.Value==info.AlgorithmId.Value,"PKCS8 encrypted roundtrip");
        Throws(()=>Pkcs8PrivateKeyInfo.DecryptAndDecode("wrong-password",encrypted,out _),"Wrong PKCS8 password accepted");
    }
    static int Main(string[] args)
    {
        try
        {
            string root=args[0];
            if(args.Length==2&&args[1]=="--verify-native")
            {
                byte[] expected=File.ReadAllBytes(Path.Combine(root,"content.bin"));
                var signedNative=new SignedCms();signedNative.Decode(File.ReadAllBytes(Path.Combine(root,"native-signed.cms")));signedNative.CheckSignature(true);Need(signedNative.ContentInfo.Content.SequenceEqual(expected),"Native signature content");
                using var nativeCert=X509Certificate2.CreateFromPem(File.ReadAllText(Path.Combine(root,"rsa-cert.pem")),File.ReadAllText(Path.Combine(root,"rsa-key.pem")));
                var encryptedNative=new EnvelopedCms();encryptedNative.Decode(File.ReadAllBytes(Path.Combine(root,"native-enveloped.cms")));encryptedNative.Decrypt(new X509Certificate2Collection(nativeCert));Need(encryptedNative.ContentInfo.Content.SequenceEqual(expected),"Native envelope content");
                Console.WriteLine("PASS source PKCS9 verifies OpenSSL CMS signature and decrypts OpenSSL CMS envelope");return 0;
            }
            var assembly=typeof(SignedCms).Assembly;
            Need(assembly.GetName().Version==new Version(9,0,0,0),"Assembly version");
            Need(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="b03f5f7f11d50a3a","Microsoft key");
            Need(Path.GetFullPath(assembly.Location)==Path.GetFullPath(Path.Combine(root,"System.Security.Cryptography.Pkcs.dll")),"Source DLL location");
            Need(assembly.GetCustomAttributesData().Any(a=>a.AttributeType.FullName=="System.Runtime.Versioning.UnsupportedOSPlatformAttribute"&&(string)a.ConstructorArguments[0].Value! =="browser"),"Browser annotation");
            var strings=JsonSerializer.Deserialize<System.Collections.Generic.Dictionary<string,string>>(File.ReadAllText(Path.Combine(root,"neutral-strings.json")))!;
            var manager=new ResourceManager("FxResources.System.Security.Cryptography.Pkcs.SR",assembly);
            foreach(var pair in strings)Need(manager.GetString(pair.Key,System.Globalization.CultureInfo.InvariantCulture)==pair.Value,"Resource "+pair.Key);
            byte[] content=Encoding.UTF8.GetBytes("owned CMS source fixture: Grüße 世界 😀\0binary\n");File.WriteAllBytes(Path.Combine(root,"content.bin"),content);
            using var rsa=RSA.Create(2048);var request=new CertificateRequest("CN=Owned Source PKCS9",rsa,HashAlgorithmName.SHA256,RSASignaturePadding.Pkcs1);
            using var certificate=request.CreateSelfSigned(DateTimeOffset.UtcNow.AddDays(-1),DateTimeOffset.UtcNow.AddDays(1));
            File.WriteAllText(Path.Combine(root,"rsa-cert.pem"),certificate.ExportCertificatePem());File.WriteAllText(Path.Combine(root,"rsa-key.pem"),rsa.ExportPkcs8PrivateKeyPem());
            Cms(root,content,certificate,rsa,"rsa");
            using var ec=ECDsa.Create(ECCurve.NamedCurves.nistP256);using var ecCert=new CertificateRequest("CN=Owned Source EC PKCS9",ec,HashAlgorithmName.SHA256).CreateSelfSigned(DateTimeOffset.UtcNow.AddDays(-1),DateTimeOffset.UtcNow.AddDays(1));
            Cms(root,content,ecCert,ec,"ecdsa");
            var envelope=new EnvelopedCms(new ContentInfo(content),new AlgorithmIdentifier(new Oid("2.16.840.1.101.3.4.1.42")));
            envelope.Encrypt(new CmsRecipient(certificate));File.WriteAllBytes(Path.Combine(root,"enveloped.cms"),envelope.Encode());
            var decoded=new EnvelopedCms();decoded.Decode(envelope.Encode());decoded.Decrypt(new X509Certificate2Collection(certificate));Need(decoded.ContentInfo.Content.SequenceEqual(content),"RSA/AES CMS decrypt");
            var safe=new Pkcs12SafeContents();safe.AddCertificate(certificate);safe.AddShroudedKey(rsa,"owned-password",new PbeParameters(PbeEncryptionAlgorithm.Aes256Cbc,HashAlgorithmName.SHA256,1000));
            var builder=new Pkcs12Builder();builder.AddSafeContentsEncrypted(safe,"owned-password",new PbeParameters(PbeEncryptionAlgorithm.Aes256Cbc,HashAlgorithmName.SHA256,1000));builder.SealWithMac("owned-password",HashAlgorithmName.SHA256,1000);
            byte[] pfx=builder.Encode();var pfxInfo=Pkcs12Info.Decode(pfx,out int consumed);Need(consumed==pfx.Length&&pfxInfo.VerifyMac("owned-password")&&!pfxInfo.VerifyMac("wrong-password"),"PKCS12 MAC/password");
            pfxInfo.AuthenticatedSafe[0].Decrypt("owned-password");Need(pfxInfo.AuthenticatedSafe[0].GetBags().Count()==2,"PKCS12 bags");File.WriteAllBytes(Path.Combine(root,"owned.pfx"),pfx);
            using var imported=X509CertificateLoader.LoadPkcs12(pfx,"owned-password",X509KeyStorageFlags.EphemeralKeySet);Need(imported.HasPrivateKey&&imported.Thumbprint==certificate.Thumbprint,"Independent BCL PFX import");
            var timestamp=Rfc3161TimestampRequest.CreateFromData(content,HashAlgorithmName.SHA256,requestedPolicyId:new Oid("1.2.3.4"),nonce:new byte[]{1,2,3},requestSignerCertificates:true);
            Need(Rfc3161TimestampRequest.TryDecode(timestamp.Encode(),out var parsed,out int size)&&size==timestamp.Encode().Length&&parsed!.GetMessageHash().Span.SequenceEqual(SHA256.HashData(content)),"RFC3161 request roundtrip");
            Throws(()=>{var bad=new SignedCms();bad.Decode(new byte[]{0x30,0x01,0xff});},"Malformed CMS accepted");
            for(int i=0;i<12;i++){var repeat=new SignedCms();repeat.Decode(File.ReadAllBytes(Path.Combine(root,"rsa-attached.cms")));repeat.CheckSignature(true);if(i%3==0){GC.Collect();GC.WaitForPendingFinalizers();}}
            Console.WriteLine("PASS source PKCS9 identity/all resources, RSA/ECDSA attached/detached/counter signatures,tampering,AES envelopes,PKCS8/PKCS12 passwords and bags,BCL PFX import,RFC3161,malformed input and12 GC iterations");return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
}
