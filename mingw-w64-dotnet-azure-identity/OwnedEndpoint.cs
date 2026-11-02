using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

sealed class OwnedEndpoint : IAsyncDisposable
{
    public const string Tenant="11111111-2222-3333-4444-555555555555";
    readonly TcpListener listener=new TcpListener(IPAddress.Loopback,0);
    readonly CancellationTokenSource stop=new CancellationTokenSource(TimeSpan.FromSeconds(75));
    readonly X509Certificate2 certificate;
    readonly RSA assertionKey;
    readonly Task task;
    public readonly string BaseUri,Authority,TokenEndpoint;
    public int SecretRequests,CertificateRequests,AuthCodeRequests,BadRequests;
    public bool CaeAuthorizationSeen;
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static string B64(byte[] data)=>Convert.ToBase64String(data).TrimEnd('=').Replace('+','-').Replace('/','_');
    static byte[] Decode(string value)=>Convert.FromBase64String(value.Replace('-','+').Replace('_','/')+new string('=',(4-value.Length%4)%4));
    public OwnedEndpoint(X509Certificate2 certificate,RSA assertionKey)
    {
        this.certificate=certificate;this.assertionKey=assertionKey;listener.Start();
        BaseUri="https://127.0.0.1:"+((IPEndPoint)listener.LocalEndpoint).Port+"/";
        Authority=BaseUri+Tenant;TokenEndpoint=Authority+"/oauth2/v2.0/token";task=Run();
    }
    string IdToken(string clientId)
    {
        string header=B64(Encoding.UTF8.GetBytes("{\"alg\":\"RS256\",\"typ\":\"JWT\"}"));
        string payload=B64(Encoding.UTF8.GetBytes("{\"oid\":\"22222222-3333-4444-5555-666666666666\",\"tid\":\""+Tenant+"\",\"preferred_username\":\"owned@example.test\",\"sub\":\"owned-sub\",\"aud\":\""+clientId+"\",\"iat\":"+DateTimeOffset.UtcNow.ToUnixTimeSeconds()+",\"exp\":"+DateTimeOffset.UtcNow.AddHours(1).ToUnixTimeSeconds()+"}"));
        byte[] message=Encoding.ASCII.GetBytes(header+"."+payload);
        return header+"."+payload+"."+B64(assertionKey.SignData(message,HashAlgorithmName.SHA256,RSASignaturePadding.Pkcs1));
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
                    Require(header.Count<32000,"bounded HTTP headers");Require(await stream.ReadAsync(one,stop.Token)==1,"HTTP header EOF");header.Add(one[0]);
                    if(header.Count>=4 && header.TakeLast(4).SequenceEqual(new byte[]{13,10,13,10}))break;
                }
                string headers=Encoding.ASCII.GetString(header.ToArray());int length=0;
                foreach(string line in headers.Split("\r\n"))if(line.StartsWith("Content-Length:",StringComparison.OrdinalIgnoreCase))length=int.Parse(line.Split(':')[1]);
                var body=new byte[length];await stream.ReadExactlyAsync(body,stop.Token);int status=200;string response;
                if(headers.StartsWith("GET "))
                {
                    Require(headers.Contains(".well-known/openid-configuration"),"owned OIDC discovery only");
                    response="{\"authorization_endpoint\":\""+Authority+"/oauth2/v2.0/authorize\",\"token_endpoint\":\""+TokenEndpoint+"\",\"issuer\":\""+Authority+"/v2.0\",\"jwks_uri\":\""+Authority+"/keys\"}";
                }
                else
                {
                    Require(headers.StartsWith("POST /"+Tenant+"/oauth2/v2.0/token "),"owned token endpoint only");
                    var form=Encoding.UTF8.GetString(body).Split('&').Select(v=>v.Split('=',2)).ToDictionary(v=>Uri.UnescapeDataString(v[0].Replace('+',' ')),v=>Uri.UnescapeDataString(v[1].Replace('+',' ')));
                    Require(form["scope"].Contains("owned-resource/.default"),"original scope serialization");
                    if(form["grant_type"]=="authorization_code")
                    {
                        Require(form["code"]=="owned-code" && form["client_secret"]=="owned λ&+ secret","authorization code and client credential preserved");
                        Require(form["redirect_uri"]=="http://localhost/owned-return","original redirect URI");
                        AuthCodeRequests++;CaeAuthorizationSeen|=form.TryGetValue("claims",out var claims) && claims.Contains("CP1",StringComparison.OrdinalIgnoreCase);
                        string clientInfo=B64(Encoding.UTF8.GetBytes("{\"uid\":\"22222222-3333-4444-5555-666666666666\",\"utid\":\""+Tenant+"\"}"));
                        response="{\"access_token\":\"owned-code-"+AuthCodeRequests+"\",\"token_type\":\"Bearer\",\"expires_in\":3600,\"scope\":\"https://owned-resource/.default\",\"client_info\":\""+clientInfo+"\",\"id_token\":\""+IdToken(form["client_id"])+"\"}";
                    }
                    else
                    {
                        Require(form["grant_type"]=="client_credentials","original client-credentials grant");
                        if(form.TryGetValue("client_secret",out string secret))
                        {
                            if(secret=="owned λ&+ secret"){SecretRequests++;response="{\"access_token\":\"owned-secret-"+SecretRequests+"\",\"token_type\":\"Bearer\",\"expires_in\":3600}";}
                            else{BadRequests++;status=400;response="{\"error\":\"invalid_client\",\"error_description\":\"owned rejected credential\",\"error_codes\":[7000215]}";}
                        }
                        else
                        {
                            Require(form["client_assertion_type"]=="urn:ietf:params:oauth:client-assertion-type:jwt-bearer","JWT client assertion type");
                            var jwt=form["client_assertion"].Split('.');Require(jwt.Length==3,"JWT framing");
                            using var jwtHeader=JsonDocument.Parse(Decode(jwt[0]));using var payload=JsonDocument.Parse(Decode(jwt[1]));
                            Require(jwtHeader.RootElement.GetProperty("alg").GetString()=="PS256","original assertion algorithm");
                            Require(jwtHeader.RootElement.GetProperty("x5t#S256").GetString()==B64(SHA256.HashData(certificate.RawData)),"original certificate thumbprint");
                            Require(payload.RootElement.GetProperty("aud").GetString()==TokenEndpoint,"JWT audience");
                            Require(payload.RootElement.GetProperty("iss").GetString()==form["client_id"] && payload.RootElement.GetProperty("sub").GetString()==form["client_id"],"JWT client identity");
                            var message=Encoding.ASCII.GetBytes(jwt[0]+"."+jwt[1]);var signature=Decode(jwt[2]);
                            Require(assertionKey.VerifyData(message,signature,HashAlgorithmName.SHA256,RSASignaturePadding.Pss),"original certificate assertion signature");
                            message[0]^=1;Require(!assertionKey.VerifyData(message,signature,HashAlgorithmName.SHA256,RSASignaturePadding.Pss),"tampered assertion rejected");
                            CertificateRequests++;response="{\"access_token\":\"owned-certificate\",\"token_type\":\"Bearer\",\"expires_in\":3600}";
                        }
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
