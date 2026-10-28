using System;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Azure.Core;
using Azure.Core.Pipeline;
using Azure.Identity;

class Program
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static async Task Main(string[] args)
    {
        using var hashes=JsonDocument.Parse(File.ReadAllBytes(args[0]));
        foreach(var assembly in new[]{typeof(ClientSecretCredential).Assembly,typeof(TokenCredential).Assembly,typeof(Microsoft.Identity.Client.ConfidentialClientApplicationBuilder).Assembly,typeof(Microsoft.Identity.Client.Extensions.Msal.MsalCacheHelper).Assembly,typeof(JsonSerializer).Assembly,typeof(BinaryData).Assembly,typeof(System.ClientModel.Primitives.ModelReaderWriter).Assembly,typeof(Microsoft.IdentityModel.Abstractions.ITelemetryClient).Assembly,typeof(ProtectedData).Assembly})
        {
            Require(Path.GetDirectoryName(assembly.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"foreign loaded runtime "+assembly.GetName().Name);
            Require(Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(assembly.Location))).ToLowerInvariant()==hashes.RootElement.GetProperty(assembly.GetName().Name).GetString(),"source runtime hash "+assembly.GetName().Name);
        }
        Require(!JsonSerializer.IsReflectionEnabledByDefault,"original source JSON contexts required");
        using var rsa=RSA.Create(2048);var request=new CertificateRequest("CN=owned-identity-loopback",rsa,HashAlgorithmName.SHA256,RSASignaturePadding.Pkcs1);
        using var ephemeral=request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-5),DateTimeOffset.UtcNow.AddHours(1));
        using var certificate=new X509Certificate2(ephemeral.Export(X509ContentType.Pfx,"owned-fixture"),"owned-fixture",X509KeyStorageFlags.UserKeySet);
        await using var endpoint=new OwnedEndpoint(certificate,rsa);byte[] expected=certificate.RawData;
        using var handler=new HttpClientHandler{UseProxy=false,AllowAutoRedirect=false,ServerCertificateCustomValidationCallback=(r,c,chain,error)=>r.RequestUri.Host=="127.0.0.1" && c!=null && c.RawData.SequenceEqual(expected)};
        using var client=new HttpClient(handler){Timeout=TimeSpan.FromSeconds(12)};var transport=new HttpClientTransport(client);
        const string clientId="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";const string secret="owned λ&+ secret";
        var context=new TokenRequestContext(new[]{"https://owned-resource/.default"});
        var options=new ClientSecretCredentialOptions{AuthorityHost=new Uri(endpoint.BaseUri),DisableInstanceDiscovery=true,Transport=transport};
        var credential=new ClientSecretCredential(OwnedEndpoint.Tenant,clientId,secret,options);
        var token=await credential.GetTokenAsync(context);Require(token.Token=="owned-secret-1" && endpoint.SecretRequests==1,"Azure.Identity through source Core/MSAL real TLS secret acquisition");
        Require(credential.GetToken(context).Token==token.Token && endpoint.SecretRequests==1,"sync cache hit");
        var certOptions=new ClientCertificateCredentialOptions{AuthorityHost=new Uri(endpoint.BaseUri),DisableInstanceDiscovery=true,Transport=transport};
        var certCredential=new ClientCertificateCredential(OwnedEndpoint.Tenant,"bbbbbbbb-cccc-dddd-eeee-ffffffffffff",certificate,certOptions);
        Require((await certCredential.GetTokenAsync(context)).Token=="owned-certificate" && endpoint.CertificateRequests==1,"certificate acquisition and independently verified RSA-PSS assertion");
        var codeOptions=new AuthorizationCodeCredentialOptions{AuthorityHost=new Uri(endpoint.BaseUri),DisableInstanceDiscovery=true,Transport=transport,RedirectUri=new Uri("http://localhost/owned-return")};
        var code=new AuthorizationCodeCredential(OwnedEndpoint.Tenant,"cccccccc-dddd-eeee-ffff-aaaaaaaaaaaa",secret,"owned-code",codeOptions);
        Require((await code.GetTokenAsync(context)).Token=="owned-code-1" && endpoint.AuthCodeRequests==1,"ported initial authorization-code branch");
        Require(code.GetToken(context).Token=="owned-code-1" && endpoint.AuthCodeRequests==1,"authorization-code silent cache hit");
        var cae=new TokenRequestContext(context.Scopes,isCaeEnabled:true);
        Require((await code.GetTokenAsync(cae)).Token=="owned-code-2" && endpoint.AuthCodeRequests==2 && endpoint.CaeAuthorizationSeen,"ported silent-miss fallback to authorization code in separate CAE cache");
        Require(code.GetToken(cae).Token=="owned-code-2" && endpoint.AuthCodeRequests==2,"CAE cache hit");
        bool rejected=false;
        try{await new ClientSecretCredential(OwnedEndpoint.Tenant,"dddddddd-eeee-ffff-aaaa-bbbbbbbbbbbb","owned-wrong",options).GetTokenAsync(context);}
        catch(AuthenticationFailedException e){rejected=e.InnerException is Microsoft.Identity.Client.MsalServiceException msal && msal.ErrorCode=="invalid_client";}
        Require(rejected && endpoint.BadRequests==1,"original authentication error wrapping");
        using var cancelled=new CancellationTokenSource();cancelled.Cancel();bool cancelledResult=false;
        try{await new ClientSecretCredential(OwnedEndpoint.Tenant,"eeeeeeee-ffff-aaaa-bbbb-cccccccccccc",secret,options).GetTokenAsync(context,cancelled.Token);}catch(OperationCanceledException){cancelledResult=true;}
        Require(cancelledResult,"original cancellation");
        string[] variables={"AZURE_TENANT_ID","AZURE_CLIENT_ID","AZURE_CLIENT_SECRET"};var saved=variables.Select(Environment.GetEnvironmentVariable).ToArray();
        try
        {
            Environment.SetEnvironmentVariable(variables[0],OwnedEndpoint.Tenant);Environment.SetEnvironmentVariable(variables[1],"ffffffff-aaaa-bbbb-cccc-dddddddddddd");Environment.SetEnvironmentVariable(variables[2],secret);
            var defaults=new DefaultAzureCredentialOptions{AuthorityHost=new Uri(endpoint.BaseUri),DisableInstanceDiscovery=true,Transport=transport,ExcludeEnvironmentCredential=false,ExcludeWorkloadIdentityCredential=true,ExcludeManagedIdentityCredential=true,ExcludeSharedTokenCacheCredential=true,ExcludeVisualStudioCredential=true,ExcludeVisualStudioCodeCredential=true,ExcludeAzureCliCredential=true,ExcludeAzurePowerShellCredential=true,ExcludeAzureDeveloperCliCredential=true,ExcludeInteractiveBrowserCredential=true};
            int before=endpoint.SecretRequests;var defaultCredential=new DefaultAzureCredential(defaults);
            Require((await defaultCredential.GetTokenAsync(context)).Token=="owned-secret-"+(before+1) && endpoint.SecretRequests==before+1,"PSResourceGet's DefaultAzureCredential path with owned process-local environment credential");
        }
        finally{for(int i=0;i<variables.Length;i++)Environment.SetEnvironmentVariable(variables[i],saved[i]);}
        Console.WriteLine("PASS original Azure.Identity real owned TLS/Core/MSAL secret/certificate flows, authorization-code initial and CAE silent-miss fallback paths, sync/async cache, DefaultAzureCredential environment selection, errors/cancellation; reflection-disabled source contexts and all nine runtime hashes");
    }
}
