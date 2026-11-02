using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using NuGet.Common;
using NuGet.Configuration;
using NuGet.Credentials;
using NuGet.Protocol;
using NuGet.Protocol.Core.Types;
using NuGet.Versioning;

static class ProtocolChecks
{
    static void Require(bool value,string message) { if(!value)throw new Exception(message); }
    sealed class Provider : ICredentialProvider
    {
        readonly Uri address;
        public Provider(Uri address) { this.address=address; }
        public string Id => "Owned loopback credential fixture";
        public int Calls;
        public Task<CredentialResponse> GetAsync(Uri uri,IWebProxy proxy,CredentialRequestType type,
            string message,bool isRetry,bool nonInteractive,CancellationToken token)
        {
            token.ThrowIfCancellationRequested();
            Require(uri.Host==address.Host && uri.Port==address.Port && nonInteractive,"credential request must remain owned and noninteractive");
            Interlocked.Increment(ref Calls);
            return Task.FromResult(new CredentialResponse(new NetworkCredential("owned-user","owned-fixture-password")));
        }
    }
    sealed class Feed : IAsyncDisposable
    {
        readonly TcpListener listener=new TcpListener(IPAddress.Loopback,0);
        readonly string directory;
        readonly Task server;
        readonly CancellationTokenSource stop=new CancellationTokenSource();
        public readonly Uri Address;
        public int Challenges,Downloads;
        public Feed(string directory)
        {
            this.directory=directory;listener.Start();
            Address=new Uri("http://127.0.0.1:"+((IPEndPoint)listener.LocalEndpoint).Port+"/");
            server=Serve();
        }
        async Task Serve()
        {
            while(!stop.IsCancellationRequested)
            {
                TcpClient client;
                try { client=await listener.AcceptTcpClientAsync(stop.Token); }
                catch(OperationCanceledException) { break; }
                using(client)
                {
                    using var stream=client.GetStream();
                    using var reader=new StreamReader(stream,Encoding.ASCII,false,4096,true);
                    string request=await reader.ReadLineAsync(stop.Token);
                    if(request==null)continue;
                    string authorization=null;
                    for(int i=0;i<100;i++)
                    {
                        string header=await reader.ReadLineAsync(stop.Token);
                        if(string.IsNullOrEmpty(header))break;
                        if(header.StartsWith("Authorization:",StringComparison.OrdinalIgnoreCase))authorization=header.Substring(14).Trim();
                    }
                    int status=200;string contentType="application/json",extra="";byte[] body;
                    string path=new Uri(Address,request.Split(' ')[1]).AbsolutePath;
                    string basic="Basic "+Convert.ToBase64String(Encoding.ASCII.GetBytes("owned-user:owned-fixture-password"));
                    if(authorization!=basic)
                    {
                        Interlocked.Increment(ref Challenges);status=401;
                        extra="WWW-Authenticate: Basic realm=\"owned-source-fixture\"\r\n";body=Array.Empty<byte>();
                    }
                    else if(path=="/v3/index.json")
                        body=JsonSerializer.SerializeToUtf8Bytes(new Dictionary<string,object> {
                            ["version"]="3.0.0",["resources"]=new[] {new Dictionary<string,string> {
                                ["@id"]=new Uri(Address,"flat/").ToString(),["@type"]="PackageBaseAddress/3.0.0"}}});
                    else if(path=="/flat/owned.root/index.json")
                        body=JsonSerializer.SerializeToUtf8Bytes(new {versions=new[] {"1.0.0","1.1.0-preview.1"}});
                    else if(path=="/flat/owned.root/1.0.0/owned.root.1.0.0.nupkg")
                    {
                        body=File.ReadAllBytes(Path.Combine(directory,"Owned.Root.1.0.0.nupkg"));
                        contentType="application/octet-stream";Interlocked.Increment(ref Downloads);
                    }
                    else {status=404;body=Array.Empty<byte>();}
                    string reason=status==200?"OK":status==401?"Unauthorized":"Not Found";
                    byte[] headers=Encoding.ASCII.GetBytes("HTTP/1.1 "+status+" "+reason+"\r\nContent-Type: "+contentType+
                        "\r\nContent-Length: "+body.Length+"\r\nConnection: close\r\n"+extra+"\r\n");
                    await stream.WriteAsync(headers,stop.Token);await stream.WriteAsync(body,stop.Token);
                }
            }
        }
        public async ValueTask DisposeAsync()
        {
            stop.Cancel();
            try {await server;} finally {listener.Stop();stop.Dispose();}
        }
    }
    public static async Task Run(string localFeed)
    {
        await using var feed=new Feed(localFeed);
        var provider=new Provider(feed.Address);
        var service=new CredentialService(new AsyncLazy<IEnumerable<ICredentialProvider>>(
            ()=>Task.FromResult<IEnumerable<ICredentialProvider>>(new[] {provider})),true,false);
        var previous=HttpHandlerResourceV3.CredentialService;
        HttpHandlerResourceV3.CredentialService=new Lazy<ICredentialService>(()=>service);
        try
        {
            using var limit=new CancellationTokenSource(TimeSpan.FromSeconds(45));
            using var cache=new SourceCacheContext {NoCache=true,DirectDownload=true,
                GeneratedTempFolder=Path.Combine(Path.GetDirectoryName(localFeed),"owned-http-temp")};
            var repository=Repository.Factory.GetCoreV3(new Uri(feed.Address,"v3/index.json").ToString());
            var resource=await repository.GetResourceAsync<FindPackageByIdResource>(limit.Token);
            var versions=(await resource.GetAllVersionsAsync("Owned.Root",cache,NullLogger.Instance,limit.Token)).ToArray();
            Require(versions.Length==2 && versions.Any(v=>v.IsPrerelease),"HTTP V3 stable/prerelease versions");
            using var output=new MemoryStream();
            Require(await resource.CopyNupkgToStreamAsync("Owned.Root",NuGetVersion.Parse("1.0.0"),output,cache,NullLogger.Instance,limit.Token),"HTTP package download");
            Require(output.ToArray().SequenceEqual(File.ReadAllBytes(Path.Combine(localFeed,"Owned.Root.1.0.0.nupkg"))),"HTTP exact package bytes");
            Require(!(await resource.GetAllVersionsAsync("Owned.Missing",cache,NullLogger.Instance,limit.Token)).Any(),"HTTP 404 missing package");
            Require(provider.Calls>0 && feed.Challenges>0 && feed.Downloads==1,"actual source credential service and HTTP authentication");
            Console.WriteLine("PASS original HTTP V3 index/flat-container, 401 credential-provider authentication, stable/prerelease versions, exact download bytes and404 missing package on owned loopback server");
        }
        finally {HttpHandlerResourceV3.CredentialService=previous;}
    }
}
