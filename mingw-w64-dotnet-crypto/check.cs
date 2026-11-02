using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Diagnostics.Metrics;
using System.Formats.Asn1;
using System.IO;
using System.Linq;
using System.Numerics;
using System.Reflection;
using System.Security.Cryptography;
using System.Security.Cryptography.Pkcs;
using System.Security.Cryptography.X509Certificates;
using System.Security.Cryptography.Xml;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Xml;

internal static class Program
{
    static void Require(bool value,string message) {if(!value)throw new Exception(message);}
    static void Throws<T>(Action action) where T:Exception {try{action();}catch(T){return;}throw new Exception("Expected "+typeof(T).Name);}
    static void Identities()
    {
        using var doc=JsonDocument.Parse(File.ReadAllText("libraries.json"));
        foreach(var lib in doc.RootElement.EnumerateArray())
        {
            string id=lib.GetProperty("id").GetString(),version=lib.GetProperty("version").GetString();
            var asm=Assembly.Load(id);
            Require(asm.GetName().Version==new Version(8,0,0,0),"Assembly version mismatch: "+id);
            string token=Convert.ToHexString(asm.GetName().GetPublicKeyToken()).ToLowerInvariant();
            Require(token==(lib.GetProperty("key").GetString()=="Microsoft"?"b03f5f7f11d50a3a":"cc7b13ffcd2ddd51"),"Signing identity mismatch: "+id);
            Require(asm.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion.StartsWith(version+"+runtime-v8.0.31")==true,"Older/shared implementation selected: "+id+" at "+asm.Location);
            Require(asm.GetCustomAttribute<AssemblyFileVersionAttribute>()?.Version=="8.0.31.0","Source file version mismatch: "+id);
            Require(asm.GetManifestResourceNames().Contains("FxResources."+id+".SR.resources"),"Resource strings missing: "+id);
            Require(Path.GetFullPath(asm.Location).StartsWith(Path.GetFullPath(AppContext.BaseDirectory),StringComparison.OrdinalIgnoreCase),"Assembly outside consumer output: "+id);
            Console.WriteLine("IDENTITY: "+asm.FullName+"; types="+asm.GetTypes().Length+"; forwards="+asm.GetForwardedTypes().Length+"; file="+asm.Location);
        }
    }
    static void Asn1()
    {
        foreach(var rules in new[]{AsnEncodingRules.BER,AsnEncodingRules.CER,AsnEncodingRules.DER})
        {
            var writer=new AsnWriter(rules);
            byte[] octets=Enumerable.Range(0,2100).Select(x=>(byte)x).ToArray();
            DateTimeOffset time=new DateTimeOffset(2026,10,26,12,34,56,TimeSpan.Zero);
            using(writer.PushSequence())
            {
                writer.WriteInteger(BigInteger.Parse("123456789012345678901234567890"));writer.WriteBoolean(true);
                writer.WriteObjectIdentifier("1.2.840.113549.1.7.2");writer.WriteCharacterString(UniversalTagNumber.UTF8String,"Grüße 世界 😀");
                writer.WriteOctetString(octets);writer.WriteBitString(new byte[]{0xa0},5);writer.WriteGeneralizedTime(time,true);
            }
            var reader=new AsnReader(writer.Encode(),rules);var sequence=reader.ReadSequence();
            Require(sequence.ReadInteger()==BigInteger.Parse("123456789012345678901234567890"),"ASN integer mismatch");
            Require(sequence.ReadBoolean()&&sequence.ReadObjectIdentifier()=="1.2.840.113549.1.7.2","ASN bool/OID mismatch");
            Require(sequence.ReadCharacterString(UniversalTagNumber.UTF8String)=="Grüße 世界 😀","ASN Unicode mismatch");
            Require(sequence.ReadOctetString().SequenceEqual(octets),"ASN large octet/constructed round-trip failed");
            Require(sequence.ReadBitString(out int unused).SequenceEqual(new byte[]{0xa0})&&unused==5,"ASN bit string mismatch");
            Require(sequence.ReadGeneralizedTime()==time,"ASN time mismatch");sequence.ThrowIfNotEmpty();reader.ThrowIfNotEmpty();
        }
        // DER rejects nonminimal integer encoding and indefinite sequence lengths.
        Throws<AsnContentException>(()=>new AsnReader(new byte[]{2,2,0,1},AsnEncodingRules.DER).ReadInteger());
        Throws<AsnContentException>(()=>new AsnReader(new byte[]{0x30,0x80,0,0},AsnEncodingRules.DER).ReadSequence());
        Throws<AsnContentException>(()=>new AsnReader(new byte[]{4,3,1},AsnEncodingRules.DER).ReadOctetString());
        Console.WriteLine("PASS: BER/CER/DER large/constructed data, integers, OIDs, Unicode, bits/time and malformed input");
    }
    static X509Certificate2 Certificate(RSA key)
    {
        var request=new CertificateRequest("CN=MSYS2 PowerShell dependency probe",key,HashAlgorithmName.SHA256,RSASignaturePadding.Pkcs1);
        return request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-1),DateTimeOffset.UtcNow.AddDays(1));
    }
    static void Pkcs(RSA key,X509Certificate2 cert)
    {
        byte[] data=Encoding.UTF8.GetBytes("source-built CMS Grüße 世界 😀");
        foreach(bool detached in new[]{false,true})
        {
            var cms=new SignedCms(new ContentInfo(data),detached);
            var signer=new CmsSigner(SubjectIdentifierType.IssuerAndSerialNumber,cert){DigestAlgorithm=new Oid("2.16.840.1.101.3.4.2.1"),IncludeOption=X509IncludeOption.EndCertOnly};
            signer.SignedAttributes.Add(new Pkcs9SigningTime(DateTime.UtcNow));cms.ComputeSignature(signer,true);
            byte[] encoded=cms.Encode();
            var decoded=detached?new SignedCms(new ContentInfo(data),true):new SignedCms();decoded.Decode(encoded);decoded.CheckSignature(true);
            Require(decoded.SignerInfos.Count==1&&decoded.ContentInfo.Content.SequenceEqual(data),"CMS content/signer lost");
            encoded[encoded.Length-1]^=1;
            Throws<CryptographicException>(()=>{var bad=detached?new SignedCms(new ContentInfo(data),true):new SignedCms();bad.Decode(encoded);bad.CheckSignature(true);});
        }
        var envelope=new EnvelopedCms(new ContentInfo(data),new AlgorithmIdentifier(new Oid("2.16.840.1.101.3.4.1.42")));
        envelope.Encrypt(new CmsRecipient(cert));
        byte[] encrypted=envelope.Encode();
        var opened=new EnvelopedCms();opened.Decode(encrypted);opened.Decrypt(new X509Certificate2Collection(cert));
        Require(opened.ContentInfo.Content.SequenceEqual(data),"CMS AES envelope round-trip failed");
        using var wrongKey=RSA.Create(2048);using var wrongCert=Certificate(wrongKey);
        Throws<CryptographicException>(()=>{var bad=new EnvelopedCms();bad.Decode(encrypted);bad.Decrypt(new X509Certificate2Collection(wrongCert));});
        var contents=new Pkcs12SafeContents();contents.AddCertificate(cert);
        var pbe=new PbeParameters(PbeEncryptionAlgorithm.Aes256Cbc,HashAlgorithmName.SHA256,1000);
        contents.AddShroudedKey(key,"probe password",pbe);
        var builder=new Pkcs12Builder();builder.AddSafeContentsEncrypted(contents,"probe password",pbe);builder.SealWithMac("probe password",HashAlgorithmName.SHA256,1000);
        byte[] pfx=builder.Encode();var info=Pkcs12Info.Decode(pfx,out int read,true);
        Require(read==pfx.Length&&info.VerifyMac("probe password")&&!info.VerifyMac("wrong"),"PKCS12 MAC/password validation failed");
        int bags=0;foreach(var safe in info.AuthenticatedSafe){safe.Decrypt("probe password");bags+=safe.GetBags().Count();}
        Require(bags==2,"PKCS12 certificate/key bags lost");
        Throws<CryptographicException>(()=>new SignedCms().Decode(new byte[]{1,2,3}));
        Console.WriteLine("PASS: native CMS attached/detached signatures, tampering, AES envelopes/wrong keys and PKCS12 password/MAC/key bags");
    }
    static void XmlCrypto(RSA key)
    {
        var doc=new XmlDocument{PreserveWhitespace=true};doc.LoadXml("<root><message>Grüße 世界 😀 &amp; source</message></root>");
        var signed=new SignedXml(doc){SigningKey=key};signed.SignedInfo.SignatureMethod=SignedXml.XmlDsigRSASHA256Url;
        var reference=new Reference(""){DigestMethod=SignedXml.XmlDsigSHA256Url};reference.AddTransform(new XmlDsigEnvelopedSignatureTransform());signed.AddReference(reference);signed.ComputeSignature();
        doc.DocumentElement.AppendChild(doc.ImportNode(signed.GetXml(),true));
        var verify=new SignedXml(doc);verify.LoadXml((XmlElement)doc.GetElementsByTagName("Signature",SignedXml.XmlDsigNamespaceUrl)[0]);
        Require(verify.CheckSignature(key),"XML RSA/SHA256 signature failed");
        using var wrong=RSA.Create(2048);Require(!verify.CheckSignature(wrong),"XML wrong key accepted");
        doc.GetElementsByTagName("message")[0].InnerText="tampered";Require(!verify.CheckSignature(key),"XML modified content accepted");
        var secret=new XmlDocument();secret.LoadXml("<root><secret>Grüße 世界 😀</secret></root>");
        using var aes=Aes.Create();aes.KeySize=256;
        byte[] bytes=new EncryptedXml().EncryptData((XmlElement)secret.DocumentElement.FirstChild,aes,false);
        var encrypted=new EncryptedData{Type=EncryptedXml.XmlEncElementUrl,EncryptionMethod=new EncryptionMethod(EncryptedXml.XmlEncAES256Url),CipherData=new CipherData(bytes)};
        encrypted.KeyInfo.AddClause(new KeyInfoName("in-memory"));
        EncryptedXml.ReplaceElement((XmlElement)secret.DocumentElement.FirstChild,encrypted,false);
        var decrypt=new EncryptedXml(secret);decrypt.AddKeyNameMapping("in-memory",aes);decrypt.DecryptDocument();
        Require(secret.DocumentElement.FirstChild.InnerText=="Grüße 世界 😀","XML AES encryption round-trip failed");
        byte[] wrapped=EncryptedXml.EncryptKey(aes.Key,key,true);Require(EncryptedXml.DecryptKey(wrapped,key,true).SequenceEqual(aes.Key),"XML RSA key wrap failed");
        Console.WriteLine("PASS: XML RSA/SHA256 signatures, wrong-key/tamper rejection, AES encryption and RSA key wrapping");
    }
    sealed class Observer:IObserver<KeyValuePair<string,object>>
    {internal int Count;public void OnNext(KeyValuePair<string,object> e){if(e.Key=="probe")Count++;}public void OnError(Exception e){throw e;}public void OnCompleted(){}}
    static void Diagnostics()
    {
        using var diagnostic=new DiagnosticListener("msys2-probe");var observer=new Observer();var subscription=diagnostic.Subscribe(observer);
        diagnostic.Write("probe",new{Value=42});subscription.Dispose();diagnostic.Write("probe",new{});Require(observer.Count==1,"DiagnosticListener subscription failed");
        int started=0,stopped=0;
        using var listener=new ActivityListener{ShouldListenTo=s=>s.Name=="msys2-probe",Sample=(ref ActivityCreationOptions<ActivityContext> options)=>ActivitySamplingResult.AllDataAndRecorded,ActivityStarted=a=>started++,ActivityStopped=a=>stopped++};
        ActivitySource.AddActivityListener(listener);
        using(var source=new ActivitySource("msys2-probe"))
        using(var parent=source.StartActivity("parent",ActivityKind.Internal))
        {
            Require(parent!=null&&parent.Recorded,"Activity creation/sample failed");parent.SetTag("unicode","Grüße 世界 😀");parent.AddEvent(new ActivityEvent("entered"));
            using var child=source.StartActivity("child");Require(child.ParentSpanId==parent.SpanId&&child.TraceId==parent.TraceId,"Activity parenting failed");
            Require(parent.GetTagItem("unicode") is string&&parent.Events.Count()==1,"Activity data lost");
        }
        Require(started==2&&stopped==2,"Activity lifecycle callbacks failed");
        long total=0;
        using var meterListener=new MeterListener{InstrumentPublished=(instrument,l)=>{if(instrument.Meter.Name=="msys2-probe")l.EnableMeasurementEvents(instrument);}};
        meterListener.SetMeasurementEventCallback<long>((instrument,measurement,tags,state)=>total+=measurement);meterListener.Start();
        using var meter=new Meter("msys2-probe");var counter=meter.CreateCounter<long>("count");counter.Add(2);counter.Add(3);Require(total==5,"Metrics counter failed");
        Console.WriteLine("PASS: DiagnosticListener subscription, Activity sampling/parenting/tags/events/lifecycle and Meter counter");
    }
    static void Encodings()
    {
        Require(HtmlEncoder.Default.Encode("<tag a=\"&\">")=="&lt;tag a=&quot;&amp;&quot;&gt;","HTML encoding failed");
        string script=JavaScriptEncoder.Default.Encode("\"\n<>&\\😀");Require(script.Contains("\\u003C")&&!script.Contains('\n')&&!script.Contains('<'),"JavaScript encoding failed");
        Require(UrlEncoder.Default.Encode("a b/&?")=="a%20b%2F%26%3F","URL encoding failed");
        Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
        var western=Encoding.GetEncoding(1252,EncoderFallback.ExceptionFallback,DecoderFallback.ExceptionFallback);
        byte[] expected={0x47,0x72,0xfc,0xdf,0x65,0x20,0x80};Require(western.GetBytes("Grüße €").SequenceEqual(expected)&&western.GetString(expected)=="Grüße €","Windows1252 mapping failed");
        var japanese=Encoding.GetEncoding(932,EncoderFallback.ExceptionFallback,DecoderFallback.ExceptionFallback);
        byte[] sjis={0x93,0xfa,0x96,0x7b,0x8c,0xea};Require(japanese.GetBytes("日本語").SequenceEqual(sjis)&&japanese.GetString(sjis)=="日本語","Shift-JIS mapping failed");
        Throws<EncoderFallbackException>(()=>western.GetBytes("😀"));Throws<DecoderFallbackException>(()=>japanese.GetString(new byte[]{0x81}));
        Console.WriteLine("PASS: HTML/JavaScript/URL escaping, Windows1252/Shift-JIS exact mappings and invalid input fallbacks");
    }
    static int Main()
    {
        Identities();Asn1();using var key=RSA.Create(2048);using var cert=Certificate(key);Pkcs(key,cert);XmlCrypto(key);Diagnostics();Encodings();
        using var process=Process.GetCurrentProcess();
        foreach(ProcessModule module in process.Modules)
        {
            Require(!module.FileName.Contains("\\Microsoft.NET\\Framework",StringComparison.OrdinalIgnoreCase),"Framework dependency: "+module.FileName);
            if(new[]{"crypt32.dll","bcrypt.dll","ncrypt.dll"}.Contains(module.ModuleName,StringComparer.OrdinalIgnoreCase))Console.WriteLine("NATIVE: "+module.FileName);
        }
        Console.WriteLine("PASS: six source-built crypto/diagnostics/encoding packages, loaded from the consumer output");return 0;
    }
}
