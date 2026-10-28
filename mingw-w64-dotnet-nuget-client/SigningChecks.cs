using System;
using System.IO;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Threading;
using System.Threading.Tasks;
using NuGet.Common;
using NuGet.Packaging;
using NuGet.Packaging.Signing;

static class SigningChecks
{
    static void Require(bool value,string message) { if(!value)throw new Exception(message); }
    public static async Task Run(string directory,string unsigned)
    {
        using var rsa=RSA.Create(2048);
        var certificateRequest=new CertificateRequest("CN=Owned NuGet source test",rsa,
            System.Security.Cryptography.HashAlgorithmName.SHA256,RSASignaturePadding.Pkcs1);
        certificateRequest.CertificateExtensions.Add(new X509BasicConstraintsExtension(false,false,0,true));
        certificateRequest.CertificateExtensions.Add(new X509KeyUsageExtension(X509KeyUsageFlags.DigitalSignature,true));
        certificateRequest.CertificateExtensions.Add(new X509EnhancedKeyUsageExtension(
            new OidCollection {new Oid("1.3.6.1.5.5.7.3.3")},true));
        using var certificate=certificateRequest.CreateSelfSigned(DateTimeOffset.UtcNow.AddHours(-1),DateTimeOffset.UtcNow.AddDays(1));
        string signed=Path.Combine(directory,"owned-signed.nupkg"),tampered=Path.Combine(directory,"owned-tampered.nupkg");
        using(var request=new AuthorSignPackageRequest(certificate,NuGet.Common.HashAlgorithmName.SHA256))
        using(var options=SigningOptions.CreateFromFilePaths(unsigned,signed,false,new X509SignatureProvider(null),NullLogger.Instance))
            await SigningUtility.SignAsync(options,request,CancellationToken.None);
        var verifier=new IntegrityVerificationProvider();
        using(var reader=new PackageArchiveReader(signed))
        {
            var signature=await reader.GetPrimarySignatureAsync(CancellationToken.None);
            Require(signature!=null && signature.Type==SignatureType.Author,"actual NuGet author signature");
            signature.SignedCms.CheckSignature(true);
            var result=await verifier.GetTrustResultAsync(reader,signature,SignedPackageVerifierSettings.GetDefault(),CancellationToken.None);
            Require(result.Trust==SignatureVerificationStatus.Valid,"signed package integrity");
        }
        File.Copy(signed,tampered);
        using(var archive=ZipFile.Open(tampered,ZipArchiveMode.Update))
        {
            archive.GetEntry("content/λ.txt").Delete();
            using var writer=new StreamWriter(archive.CreateEntry("content/λ.txt").Open());
            writer.Write("tampered owned payload");
        }
        using(var reader=new PackageArchiveReader(tampered))
        {
            var signature=await reader.GetPrimarySignatureAsync(CancellationToken.None);
            Require(signature!=null,"tamper fixture retains signature");
            var result=await verifier.GetTrustResultAsync(reader,signature,SignedPackageVerifierSettings.GetDefault(),CancellationToken.None);
            Require(result.Trust==SignatureVerificationStatus.Suspect,"modified package must fail integrity verification");
        }
        Console.WriteLine("PASS original NuGet author signing, CMS cryptographic verification, valid package integrity and tampered-package rejection with an in-memory owned certificate");
    }
}
