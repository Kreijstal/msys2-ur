using System;
using System.IdentityModel.Selectors;
using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.ServiceModel;
using System.ServiceModel.Security;
using System.Threading.Tasks;

internal static class SecurityProbe
{
    private sealed class Pin(byte[] expected,bool reject) : X509CertificateValidator
    {
        internal int Calls;
        public override void Validate(X509Certificate2 certificate)
        {
            Calls++;
            if(reject || !CryptographicOperations.FixedTimeEquals(expected,SHA256.HashData(certificate.RawData)))
                throw new AuthenticationException("Fixture certificate rejected");
        }
    }
    static async Task<string> Peer(TcpListener listener,X509Certificate2 certificate,bool reject)
    {
        using var client=await listener.AcceptTcpClientAsync();
        using var tls=new SslStream(client.GetStream(),false);
        try
        {
            await tls.AuthenticateAsServerAsync(new SslServerAuthenticationOptions{
                ServerCertificate=certificate,EnabledSslProtocols=SslProtocols.Tls12|SslProtocols.Tls13});
            if(reject)
            {
                byte[] first=new byte[1];
                if(await tls.ReadAsync(first)!=0)throw new Exception("SOAP bytes sent after certificate rejection");
                return "rejected";
            }
            return await Probe.ServeSoap(tls);
        }
        catch(Exception error) when(reject && (error is System.IO.IOException || error is AuthenticationException))
        {return "rejected";}
    }
    internal static async Task Run()
    {
        using var key=RSA.Create(2048);
        var request=new CertificateRequest("CN=localhost",key,HashAlgorithmName.SHA256,RSASignaturePadding.Pkcs1);
        var names=new SubjectAlternativeNameBuilder();names.AddDnsName("localhost");names.AddIpAddress(IPAddress.Loopback);
        request.CertificateExtensions.Add(names.Build());
        using var created=request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-5),DateTimeOffset.UtcNow.AddHours(1));
        // Schannel needs an import-backed private key, rather than the ephemeral
        // CNG key returned by CreateSelfSigned. Disposal removes the key container.
        using var certificate=new X509Certificate2(created.Export(X509ContentType.Pfx));
        foreach(bool reject in new[]{false,true})
        {
            var listener=new TcpListener(IPAddress.Loopback,0);listener.Start();
            try
            {
                int port=((IPEndPoint)listener.LocalEndpoint).Port;
                var peer=Peer(listener,certificate,reject);
                var binding=new BasicHttpsBinding(BasicHttpsSecurityMode.Transport){OpenTimeout=TimeSpan.FromSeconds(10),SendTimeout=TimeSpan.FromSeconds(10)};
                var factory=new ChannelFactory<IEcho>(binding,new EndpointAddress("https://127.0.0.1:"+port+"/echo"));
                var validator=new Pin(SHA256.HashData(certificate.RawData),reject);
                factory.Credentials.ServiceCertificate.SslCertificateAuthentication=new X509ServiceCertificateAuthentication{
                    CertificateValidationMode=X509CertificateValidationMode.Custom,CustomCertificateValidator=validator};
                bool rejected=false;
                try
                {
                    var channel=factory.CreateChannel();
                    string result=channel.Echo("source-built SOAP & XML");
                    if(reject || result!="source-built SOAP & XML")throw new Exception("HTTPS result/rejection");
                    ((IClientChannel)channel).Close();factory.Close();
                }
                catch(CommunicationException) when(reject && validator.Calls>0){rejected=true;factory.Abort();}
                catch {factory.Abort();if(peer.IsFaulted)Console.Error.WriteLine(peer.Exception);throw;}
                if(validator.Calls==0 || reject!=rejected)throw new Exception("certificate policy was not enforced");
                string received=await peer.WaitAsync(TimeSpan.FromSeconds(10));
                if(!reject && received!="source-built SOAP & XML")throw new Exception("TLS peer SOAP payload");
            }
            finally {listener.Stop();}
        }
        Console.WriteLine("PASS: BasicHttpsBinding native TLS SOAP call; custom X509 pin accepts/rejects the fixture certificate");
    }
}
