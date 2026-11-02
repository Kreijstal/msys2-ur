using System;
using System.IO;
using System.Linq;
using System.Resources;
using System.Security.Cryptography;
using System.Security.Cryptography.Xml;
using System.Text;
using System.Text.Json;
using System.Xml;

static class Probe
{
    static void Need(bool value,string label){if(!value)throw new Exception(label);}
    static byte[] Canonical(XmlDocument document)
    {
        var transform=new XmlDsigC14NTransform();transform.LoadInput(document);
        using var stream=(Stream)transform.GetOutput(typeof(Stream));using var output=new MemoryStream();stream.CopyTo(output);return output.ToArray();
    }
    static int Main(string[] args)
    {
        try
        {
            string root=args[0];var assembly=typeof(SignedXml).Assembly;
            Need(assembly.GetName().Version==new Version(9,0,0,0),"Assembly version");
            Need(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="cc7b13ffcd2ddd51","Open signing identity");
            Need(Path.GetFullPath(assembly.Location)==Path.GetFullPath(Path.Combine(root,"System.Security.Cryptography.Xml.dll")),"Exact source XML DLL");
            var strings=JsonSerializer.Deserialize<System.Collections.Generic.Dictionary<string,string>>(File.ReadAllText(Path.Combine(root,"neutral-strings.json")))!;
            var manager=new ResourceManager("FxResources.System.Security.Cryptography.Xml.SR",assembly);
            foreach(var pair in strings)Need(manager.GetString(pair.Key,System.Globalization.CultureInfo.InvariantCulture)==pair.Value,"Resource "+pair.Key);
            var canonical=new XmlDocument{PreserveWhitespace=true};canonical.LoadXml("<r z='2' a='1'><x/></r>");
            Need(Encoding.UTF8.GetString(Canonical(canonical))=="<r a=\"1\" z=\"2\"><x></x></r>","Canonical sorting/empty element vector");
            using var rsa=RSA.Create(2048);var document=new XmlDocument{PreserveWhitespace=true};document.LoadXml("<owned><message>Grüße 世界 😀</message></owned>");
            var signer=new SignedXml(document){SigningKey=rsa};signer.SignedInfo!.SignatureMethod=SignedXml.XmlDsigRSASHA256Url;
            var reference=new Reference(""){DigestMethod=SignedXml.XmlDsigSHA256Url};reference.AddTransform(new XmlDsigEnvelopedSignatureTransform());signer.AddReference(reference);signer.ComputeSignature();
            var signature=signer.GetXml();document.DocumentElement!.AppendChild(document.ImportNode(signature,true));
            var verifier=new SignedXml(document);verifier.LoadXml((XmlElement)document.GetElementsByTagName("Signature",SignedXml.XmlDsigNamespaceUrl)[0]!);Need(verifier.CheckSignature(rsa),"RSA-SHA256 enveloped XML signature");
            document.Save(Path.Combine(root,"signed.xml"));
            var signedInfo=new XmlDocument{PreserveWhitespace=true};signedInfo.LoadXml(signature["SignedInfo",SignedXml.XmlDsigNamespaceUrl]!.OuterXml);
            File.WriteAllBytes(Path.Combine(root,"signed-info.bin"),Canonical(signedInfo));File.WriteAllBytes(Path.Combine(root,"signature.bin"),signer.Signature.SignatureValue!);File.WriteAllText(Path.Combine(root,"public.pem"),rsa.ExportSubjectPublicKeyInfoPem());
            document.GetElementsByTagName("message")[0]!.InnerText="tampered";Need(!verifier.CheckSignature(rsa),"Changed XML content rejected");
            var encryptedDocument=new XmlDocument{PreserveWhitespace=true};encryptedDocument.LoadXml("<owned><secret>世界 😀 &amp; Ω</secret></owned>");using var aes=Aes.Create();aes.KeySize=256;
            var encryption=new EncryptedXml(encryptedDocument);var element=(XmlElement)encryptedDocument.DocumentElement!.FirstChild!;byte[] encrypted=encryption.EncryptData(element,aes,false);
            var data=new EncryptedData{Type=EncryptedXml.XmlEncElementUrl,EncryptionMethod=new EncryptionMethod(EncryptedXml.XmlEncAES256Url),CipherData=new CipherData(encrypted)};
            EncryptedXml.ReplaceElement(element,data,false);byte[] plaintext=encryption.DecryptData(data,aes);encryption.ReplaceData((XmlElement)encryptedDocument.DocumentElement.FirstChild!,plaintext);
            Need(encryptedDocument.DocumentElement.InnerText=="世界 😀 & Ω","AES XML encrypt/replace/decrypt");
            byte[] key=Convert.FromHexString("00112233445566778899AABBCCDDEEFF");using var kek=Aes.Create();kek.Key=Convert.FromHexString("000102030405060708090A0B0C0D0E0F");
            byte[] wrapped=EncryptedXml.EncryptKey(key,kek);Need(EncryptedXml.DecryptKey(wrapped,kek).SequenceEqual(key),"AES key wrap");File.WriteAllBytes(Path.Combine(root,"wrap-input.bin"),key);File.WriteAllBytes(Path.Combine(root,"wrapped.bin"),wrapped);
            byte[] rsaWrapped=EncryptedXml.EncryptKey(key,rsa,true);Need(EncryptedXml.DecryptKey(rsaWrapped,rsa,true).SequenceEqual(key),"RSA OAEP XML key wrap");
            var base64=new XmlDsigBase64Transform();base64.LoadInput(new MemoryStream(Encoding.ASCII.GetBytes(Convert.ToBase64String(key))));using(var output=(Stream)base64.GetOutput(typeof(Stream))){using var buffer=new MemoryStream();output.CopyTo(buffer);Need(buffer.ToArray().SequenceEqual(key),"Base64 transform");}
            for(int i=0;i<12;i++){Need(EncryptedXml.DecryptKey(EncryptedXml.EncryptKey(key,kek),kek).SequenceEqual(key),"Repeated XML key lifetime");if(i%3==0){GC.Collect();GC.WaitForPendingFinalizers();}}
            Console.WriteLine("PASS source Cryptography.Xml9 identity/all94 strings,canonicalization,RSA-SHA256 signatures/tamper,AES XML encryption,RSA/AES key wrapping,Base64 and12 GC cases");return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
}
