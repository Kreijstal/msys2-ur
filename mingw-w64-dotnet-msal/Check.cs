using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Identity.Client;
using Microsoft.Identity.Client.Extensions.Msal;

class Program
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static string B64(byte[] data)=>Convert.ToBase64String(data).TrimEnd('=').Replace('+','-').Replace('/','_');
    static byte[] Decode(string value)=>Convert.FromBase64String(value.Replace('-','+').Replace('_','/')+new string('=',(4-value.Length%4)%4));
    sealed class Factory : IMsalHttpClientFactory,IDisposable
    {
        readonly HttpClient client;
        public Factory(X509Certificate2 certificate)
        {
            byte[] expected=certificate.RawData;
            client=new HttpClient(new HttpClientHandler{UseProxy=false,AllowAutoRedirect=false,
                ServerCertificateCustomValidationCallback=(request,cert,chain,error)=>request.RequestUri.Host=="127.0.0.1" && cert!=null && cert.RawData.SequenceEqual(expected)}){Timeout=TimeSpan.FromSeconds(12)};
        }
        public HttpClient GetHttpClient()=>client;
        public void Dispose()=>client.Dispose();
    }
    sealed class Endpoint : IAsyncDisposable
    {
        readonly TcpListener listener=new TcpListener(IPAddress.Loopback,0);
        readonly CancellationTokenSource stop=new CancellationTokenSource(TimeSpan.FromSeconds(75));
        readonly X509Certificate2 certificate;
        readonly RSA assertionKey;
        readonly Task task;
        public readonly string Authority,TokenEndpoint;
        public int SecretRequests,CertificateRequests,BadRequests;
        const string Tenant="11111111-2222-3333-4444-555555555555";
        public Endpoint(X509Certificate2 certificate,RSA assertionKey)
        {
            this.certificate=certificate;this.assertionKey=assertionKey;
            listener.Start();Authority="https://127.0.0.1:"+((IPEndPoint)listener.LocalEndpoint).Port+"/"+Tenant;
            TokenEndpoint=Authority+"/oauth2/v2.0/token";task=Run();
        }
        async Task Run()
        {
            try
            {
                while(true)
                {
                    using var client=await listener.AcceptTcpClientAsync(stop.Token);
                    using var stream=new SslStream(client.GetStream(),false);
                    await stream.AuthenticateAsServerAsync(new SslServerAuthenticationOptions{ServerCertificate=certificate,EnabledSslProtocols=SslProtocols.Tls12,ApplicationProtocols=new List<SslApplicationProtocol>{SslApplicationProtocol.Http11}},stop.Token);
                    var header=new List<byte>();var one=new byte[1];
                    while(true)
                    {
                        Require(header.Count<32000,"bounded HTTP headers");
                        Require(await stream.ReadAsync(one,stop.Token)==1,"HTTP header EOF");header.Add(one[0]);
                        if(header.Count>=4 && header.TakeLast(4).SequenceEqual(new byte[]{13,10,13,10}))break;
                    }
                    string headers=Encoding.ASCII.GetString(header.ToArray());
                    int length=0;
                    foreach(string line in headers.Split("\r\n"))if(line.StartsWith("Content-Length:",StringComparison.OrdinalIgnoreCase))length=int.Parse(line.Split(':')[1]);
                    var bytes=new byte[length];await stream.ReadExactlyAsync(bytes,stop.Token);
                    int status=200;string response;
                    if(headers.StartsWith("GET "))
                    {
                        Require(headers.Contains(".well-known/openid-configuration"),"only owned OIDC discovery");
                        response="{\"authorization_endpoint\":\""+Authority+"/oauth2/v2.0/authorize\",\"token_endpoint\":\""+TokenEndpoint+"\",\"issuer\":\""+Authority+"/v2.0\",\"jwks_uri\":\""+Authority+"/keys\"}";
                    }
                    else
                    {
                        Require(headers.StartsWith("POST /"+Tenant+"/oauth2/v2.0/token "),"only owned token endpoint");
                        var form=Encoding.UTF8.GetString(bytes).Split('&').Select(v=>v.Split('=',2)).ToDictionary(v=>Uri.UnescapeDataString(v[0].Replace('+',' ')),v=>Uri.UnescapeDataString(v[1].Replace('+',' ')));
                        Require(form["grant_type"]=="client_credentials" && form["scope"].Contains("owned-resource/.default"),"original OAuth grant/scope serialization");
                        if(form.TryGetValue("client_secret",out string secret))
                        {
                            if(secret=="owned λ&+ secret") {SecretRequests++;response="{\"access_token\":\"owned-secret-"+SecretRequests+"\",\"token_type\":\"Bearer\",\"expires_in\":3600,\"ext_expires_in\":3600}";}
                            else {BadRequests++;status=400;response="{\"error\":\"invalid_client\",\"error_description\":\"owned rejected credential\",\"error_codes\":[7000215]}";}
                        }
                        else
                        {
                            Require(form["client_assertion_type"]=="urn:ietf:params:oauth:client-assertion-type:jwt-bearer","JWT client assertion type");
                            var jwt=form["client_assertion"].Split('.');Require(jwt.Length==3,"signed JWT framing");
                            using var jwtHeader=JsonDocument.Parse(Decode(jwt[0]));using var payload=JsonDocument.Parse(Decode(jwt[1]));
                            Require(jwtHeader.RootElement.GetProperty("alg").GetString()=="PS256","original modern certificate assertion algorithm");
                            Require(jwtHeader.RootElement.GetProperty("x5t#S256").GetString()==B64(SHA256.HashData(certificate.RawData)),"original SHA256 certificate thumbprint");
                            Require(payload.RootElement.GetProperty("aud").GetString()==TokenEndpoint,"JWT audience");
                            Require(payload.RootElement.GetProperty("iss").GetString()==form["client_id"] && payload.RootElement.GetProperty("sub").GetString()==form["client_id"],"JWT client identity");
                            Require(long.Parse(payload.RootElement.GetProperty("exp").GetString(),System.Globalization.CultureInfo.InvariantCulture)>DateTimeOffset.UtcNow.ToUnixTimeSeconds(),"original string-encoded JWT expiration");
                            var signingBytes=Encoding.ASCII.GetBytes(jwt[0]+"."+jwt[1]);var signature=Decode(jwt[2]);
                            Require(assertionKey.VerifyData(signingBytes,signature,HashAlgorithmName.SHA256,RSASignaturePadding.Pss),"original MSAL RSA-PSS assertion signature");
                            signingBytes[0]^=1;Require(!assertionKey.VerifyData(signingBytes,signature,HashAlgorithmName.SHA256,RSASignaturePadding.Pss),"tampered assertion rejected");
                            CertificateRequests++;response="{\"access_token\":\"owned-certificate\",\"token_type\":\"Bearer\",\"expires_in\":3600}";
                        }
                    }
                    byte[] content=Encoding.UTF8.GetBytes(response);
                    await stream.WriteAsync(Encoding.ASCII.GetBytes("HTTP/1.1 "+status+" Owned\r\nContent-Type: application/json\r\nContent-Length: "+content.Length+"\r\nConnection: close\r\n\r\n"),stop.Token);
                    await stream.WriteAsync(content,stop.Token);
                }
            }
            catch(OperationCanceledException)when(stop.IsCancellationRequested){}
        }
        public async ValueTask DisposeAsync(){stop.Cancel();listener.Stop();await task;stop.Dispose();}
    }
    static async Task Main(string[] args)
    {
        using var hashes=JsonDocument.Parse(File.ReadAllBytes(args[0]));
        foreach(var assembly in new[]{typeof(ConfidentialClientApplicationBuilder).Assembly,typeof(MsalCacheHelper).Assembly,typeof(JsonSerializer).Assembly,typeof(Microsoft.IdentityModel.Abstractions.ITelemetryClient).Assembly,typeof(ProtectedData).Assembly})
        {
            Require(Path.GetDirectoryName(assembly.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"foreign loaded dependency "+assembly.GetName().Name);
            Require(Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(assembly.Location))).ToLowerInvariant()==hashes.RootElement.GetProperty(assembly.GetName().Name).GetString(),"source runtime hash "+assembly.GetName().Name);
        }
        Require(!JsonSerializer.IsReflectionEnabledByDefault,"original MSAL source context must handle JSON");
        using var rsa=RSA.Create(2048);
        var request=new CertificateRequest("CN=owned-msal-loopback",rsa,HashAlgorithmName.SHA256,RSASignaturePadding.Pkcs1);
        using var ephemeral=request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-5),DateTimeOffset.UtcNow.AddHours(1));
        // Schannel needs a temporary user key container; no certificate store is used.
        using var certificate=new X509Certificate2(ephemeral.Export(X509ContentType.Pfx,"owned-fixture"),"owned-fixture",X509KeyStorageFlags.UserKeySet);
        await using var endpoint=new Endpoint(certificate,rsa);using var factory=new Factory(certificate);
        var scopes=new[]{"https://owned-resource/.default"};const string clientId="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
        IConfidentialClientApplication SecretApp(string secret)=>ConfidentialClientApplicationBuilder.Create(clientId).WithAuthority(endpoint.Authority,false).WithInstanceDiscovery(false).WithHttpClientFactory(factory).WithClientSecret(secret).Build();
        var app=SecretApp("owned λ&+ secret");
        string cacheRoot=Path.Combine(Path.GetFullPath(args[1]),"owned-dpapi");Directory.CreateDirectory(cacheRoot);
        string cachePath=Path.Combine(cacheRoot,"tokens.bin");Require(!File.Exists(cachePath),"owned cache starts absent");
        var properties=new StorageCreationPropertiesBuilder("tokens.bin",cacheRoot).Build();
        var cache=await MsalCacheHelper.CreateAsync(properties);cache.VerifyPersistence();cache.RegisterCache(app.AppTokenCache);
        try
        {
            var token=await app.AcquireTokenForClient(scopes).ExecuteAsync();
            Require(token.AccessToken=="owned-secret-1" && endpoint.SecretRequests==1,"real TLS client-secret token acquisition and Unicode form encoding");
            var cached=await app.AcquireTokenForClient(scopes).ExecuteAsync();
            Require(cached.AccessToken==token.AccessToken && cached.AuthenticationResultMetadata.TokenSource==TokenSource.Cache && endpoint.SecretRequests==1,"in-memory cache avoids HTTP");
            var refreshed=await app.AcquireTokenForClient(scopes).WithForceRefresh(true).ExecuteAsync();
            Require(refreshed.AccessToken=="owned-secret-2" && endpoint.SecretRequests==2,"force refresh sends new request");
            byte[] plain=cache.LoadUnencryptedTokenCache(),encrypted=File.ReadAllBytes(cachePath);
            Require(Encoding.UTF8.GetString(plain).Contains(refreshed.AccessToken),"real MSAL cache serialization/persistence");
            Require(!encrypted.SequenceEqual(plain) && !Encoding.UTF8.GetString(encrypted).Contains(refreshed.AccessToken),"original Windows DPAPI encrypts the owned cache");
            var reopened=SecretApp("owned λ&+ secret");var reopenedCache=await MsalCacheHelper.CreateAsync(properties);reopenedCache.RegisterCache(reopened.AppTokenCache);
            try {var result=await reopened.AcquireTokenForClient(scopes).ExecuteAsync();Require(result.AccessToken==refreshed.AccessToken && result.AuthenticationResultMetadata.TokenSource==TokenSource.Cache && endpoint.SecretRequests==2,"new application decrypts persisted cache without HTTP");}
            finally{reopenedCache.UnregisterCache(reopened.AppTokenCache);}
            var certificateApp=ConfidentialClientApplicationBuilder.Create("bbbbbbbb-cccc-dddd-eeee-ffffffffffff").WithAuthority(endpoint.Authority,false).WithInstanceDiscovery(false).WithHttpClientFactory(factory).WithCertificate(certificate).Build();
            var certificateToken=await certificateApp.AcquireTokenForClient(scopes).ExecuteAsync();
            Require(certificateToken.AccessToken=="owned-certificate" && endpoint.CertificateRequests==1,"original certificate credential and verified client assertion");
            bool rejected=false;try{await SecretApp("owned-wrong").AcquireTokenForClient(scopes).WithForceRefresh(true).ExecuteAsync();}catch(MsalServiceException e){rejected=e.ErrorCode=="invalid_client" && e.StatusCode==400;}
            Require(rejected && endpoint.BadRequests==1,"original OAuth error propagation");
            using var cancelled=new CancellationTokenSource();cancelled.Cancel();bool cancelledResult=false;
            try{await app.AcquireTokenForClient(scopes).WithForceRefresh(true).ExecuteAsync(cancelled.Token);}catch(OperationCanceledException){cancelledResult=true;}
            Require(cancelledResult,"original cancellation");
            cache.UnregisterCache(app.AppTokenCache);
        }
        finally
        {
            cache.UnregisterCache(app.AppTokenCache);
            if(Directory.Exists(cacheRoot))Directory.Delete(cacheRoot,true);
        }
        Console.WriteLine("PASS original MSAL real pinned-loopback TLS/OIDC/client-secret/certificate JWT verification, Unicode forms, cache/force-refresh, DPAPI encrypted persistence/reopen, OAuth errors/cancellation and source contexts with reflection disabled; all five source runtime hashes match");
    }
}
