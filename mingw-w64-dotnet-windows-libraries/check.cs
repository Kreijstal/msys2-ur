using System;
using System.Diagnostics;
using System.DirectoryServices.Protocols;
using System.IO;
using System.IO.Compression;
using System.IO.Packaging;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Reflection;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Win32;

internal static class Program
{
    static void Require(bool value, string message) { if (!value) throw new Exception(message); }
    static void Throws<T>(Action action) where T:Exception
    { try { action(); } catch (T) { return; } throw new Exception("Expected "+typeof(T).Name); }

    static void Identity(Type type, string version)
    {
        Assembly assembly=type.Assembly;
        string token=Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant();
        Require(token=="b03f5f7f11d50a3a", "Wrong public key: "+assembly.FullName);
        Require(assembly.GetName().Version==new Version(8,0,0,0), "Wrong assembly version: "+assembly.FullName);
        Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion.StartsWith(version+"+runtime-v8.0.31")==true, "Wrong source/version: "+assembly.FullName);
        Require(assembly.GetManifestResourceNames().Contains("FxResources."+assembly.GetName().Name+".SR.resources"), "Resources missing: "+assembly.FullName);
        // Resolve every declared type to detect missing managed dependencies.
        Console.WriteLine("IDENTITY: "+assembly.FullName+"; types="+assembly.GetTypes().Length);
    }

    static void RegistryAcl()
    {
        Identity(typeof(RegistryAclExtensions),"8.0.0");
        using var key=Registry.CurrentUser.OpenSubKey("Software", RegistryKeyPermissionCheck.ReadSubTree, RegistryRights.ReadPermissions);
        Require(key!=null,"HKCU Software missing");
        RegistrySecurity security=key.GetAccessControl(AccessControlSections.Owner|AccessControlSections.Access);
        Require(security.GetOwner(typeof(SecurityIdentifier)) is SecurityIdentifier,"Registry owner missing");
        Require(security.GetSecurityDescriptorBinaryForm().Length>20,"Registry security descriptor missing");
        Require(security.GetAccessRules(true,true,typeof(SecurityIdentifier)).Count>0,"Registry DACL missing");
        Throws<ArgumentNullException>(()=>RegistryAclExtensions.GetAccessControl(null));
        Console.WriteLine("PASS: read-only native registry owner/DACL and null validation");
    }

    static void Dpapi()
    {
        Identity(typeof(ProtectedData),"8.0.0");
        byte[] data=Encoding.UTF8.GetBytes("PowerShell source-built DPAPI Grüße 世界 😀");
        byte[] entropy=RandomNumberGenerator.GetBytes(24);
        foreach (var scope in new[]{DataProtectionScope.CurrentUser,DataProtectionScope.LocalMachine})
        {
            byte[] encrypted=ProtectedData.Protect(data,entropy,scope);
            Require(!encrypted.SequenceEqual(data),"DPAPI did not encrypt");
            Require(ProtectedData.Unprotect(encrypted,entropy,scope).SequenceEqual(data),"DPAPI round-trip failed");
            Throws<CryptographicException>(()=>ProtectedData.Unprotect(encrypted,new byte[]{42},scope));
            encrypted[encrypted.Length-1]^=1;
            Throws<CryptographicException>(()=>ProtectedData.Unprotect(encrypted,entropy,scope));
        }
        Throws<ArgumentNullException>(()=>ProtectedData.Protect(null,null,DataProtectionScope.CurrentUser));
        Throws<CryptographicException>(()=>ProtectedData.Unprotect(new byte[]{1,2,3},null,DataProtectionScope.CurrentUser));
        Console.WriteLine("PASS: native DPAPI user/machine round-trips, entropy, tampering and invalid input");
    }

    static void Packaging()
    {
        Identity(typeof(Package),"8.0.1");
        using var memory=new MemoryStream();
        var uri=PackUriHelper.CreatePartUri(new Uri("/data/message.xml",UriKind.Relative));
        const string content="<message>Grüße 世界 😀 &amp; source</message>";
        using (var package=Package.Open(memory,FileMode.Create,FileAccess.ReadWrite))
        {
            package.PackageProperties.Title="PowerShell packaging probe";
            var part=package.CreatePart(uri,"application/xml",CompressionOption.Maximum);
            using (var writer=new StreamWriter(part.GetStream(FileMode.Create,FileAccess.Write),new UTF8Encoding(false))) writer.Write(content);
            package.CreateRelationship(uri,TargetMode.Internal,"urn:msys2:probe","rId1");
        }
        byte[] blob=memory.ToArray();
        using (var zip=new ZipArchive(new MemoryStream(blob),ZipArchiveMode.Read))
            Require(zip.GetEntry("[Content_Types].xml")!=null && zip.GetEntry("data/message.xml")!=null,"OPC ZIP entries missing");
        using (var package=Package.Open(new MemoryStream(blob),FileMode.Open,FileAccess.Read))
        {
            Require(package.PackageProperties.Title=="PowerShell packaging probe","Package properties lost");
            var relationship=package.GetRelationship("rId1");
            Require(relationship.TargetUri==uri && relationship.RelationshipType=="urn:msys2:probe","Relationship lost");
            using var reader=new StreamReader(package.GetPart(uri).GetStream(FileMode.Open,FileAccess.Read));
            Require(reader.ReadToEnd()==content,"Compressed Unicode part lost");
            Throws<IOException>(()=>package.CreatePart(new Uri("/no-write",UriKind.Relative),"text/plain"));
        }
        Throws<ArgumentException>(()=>PackUriHelper.CreatePartUri(new Uri("https://example.invalid/part")));
        Console.WriteLine("PASS: OPC ZIP compressed Unicode parts, metadata, relationships and invalid/read-only operations");
    }

    static void Ldap()
    {
        Identity(typeof(LdapConnection),"8.0.2");
        byte[] encoded=BerConverter.Encode("{ibso}",42,true,"Grüße 世界",new byte[]{0,1,255});
        object[] decoded=BerConverter.Decode("{ibaO}",encoded);
        Require((int)decoded[0]==42 && (bool)decoded[1] && (string)decoded[2]=="Grüße 世界" && ((byte[])decoded[3]).SequenceEqual(new byte[]{0,1,255}),"Native BER round-trip failed");
        Throws<ArgumentNullException>(()=>BerConverter.Encode(null));
        Throws<BerConversionException>(()=>BerConverter.Decode("{i}",new byte[]{0xff}));
        using var connection=new LdapConnection(new LdapDirectoryIdentifier("127.0.0.1",389));
        connection.SessionOptions.ProtocolVersion=3;
        Require(connection.SessionOptions.ProtocolVersion==3,"LDAP session protocol getter/setter failed");
        connection.AuthType=AuthType.Negotiate;
        connection.Timeout=TimeSpan.FromSeconds(2);
        var request=new SearchRequest("dc=example,dc=invalid","(objectClass=*)",SearchScope.Subtree,"cn");
        Require(request.Attributes.Count==1,"LDAP search request failed");
        var control=new PageResultRequestControl(32);
        Require(BerConverter.Decode("{iO}",control.GetValue()).Length==2,"LDAP page control native BER failed");
        Console.WriteLine("PASS: native Wldap32 BER, LDAP handle/options and search/control construction (no server bind)");
    }

    sealed class LoopbackServer:IAsyncDisposable
    {
        readonly TcpListener listener=new TcpListener(IPAddress.Loopback,0);
        readonly CancellationTokenSource stop=new CancellationTokenSource();
        readonly Task worker;
        internal readonly Uri BaseUri;
        internal LoopbackServer()
        {
            listener.Start();
            BaseUri=new Uri("http://127.0.0.1:"+((IPEndPoint)listener.LocalEndpoint).Port+"/");
            worker=Run();
        }
        async Task Run()
        {
            try
            {
                while(!stop.IsCancellationRequested)
                {
                    using var client=await listener.AcceptTcpClientAsync(stop.Token);
                    using var stream=client.GetStream();
                    using var reader=new StreamReader(stream,Encoding.ASCII,false,1024,true);
                    string first=await reader.ReadLineAsync(stop.Token);
                    string line;
                    while(!string.IsNullOrEmpty(line=await reader.ReadLineAsync(stop.Token))) { }
                    string path=first.Split(' ')[1];
                    if(path=="/slow") { await Task.Delay(Timeout.Infinite,stop.Token); continue; }
                    string status="200 OK",headers="";
                    byte[] body;
                    if(path=="/redirect") { status="302 Found"; headers="Location: /gzip\r\n"; body=Array.Empty<byte>(); }
                    else if(path=="/gzip")
                    {
                        using var compressed=new MemoryStream();
                        using(var gzip=new GZipStream(compressed,CompressionLevel.SmallestSize,true)) gzip.Write(Encoding.UTF8.GetBytes("WinHTTP Grüße 世界 😀"));
                        body=compressed.ToArray(); headers="Content-Encoding: gzip\r\nX-Msys2-Probe: source\r\n";
                    }
                    else { status="404 Not Found"; body=Encoding.UTF8.GetBytes("missing"); }
                    await stream.WriteAsync(Encoding.ASCII.GetBytes("HTTP/1.1 "+status+"\r\nConnection: close\r\nContent-Type: text/plain; charset=utf-8\r\n"+headers+"Content-Length: "+body.Length+"\r\n\r\n"),stop.Token);
                    await stream.WriteAsync(body,stop.Token);
                }
            }
            catch(OperationCanceledException) when(stop.IsCancellationRequested) { }
        }
        public async ValueTask DisposeAsync() { stop.Cancel(); listener.Stop(); await worker; stop.Dispose(); }
    }

    static async Task WinHttp()
    {
        Identity(typeof(WinHttpHandler),"8.0.3");
        await using var server=new LoopbackServer();
        using var handler=new WinHttpHandler { WindowsProxyUsePolicy=WindowsProxyUsePolicy.DoNotUseProxy, AutomaticDecompression=DecompressionMethods.GZip };
        using var client=new HttpClient(handler) { Timeout=TimeSpan.FromSeconds(15) };
        using(var response=await client.GetAsync(new Uri(server.BaseUri,"redirect")))
        {
            Require(response.IsSuccessStatusCode && response.RequestMessage.RequestUri.AbsolutePath=="/gzip","Native WinHTTP redirect failed");
            Require((await response.Content.ReadAsStringAsync())=="WinHTTP Grüße 世界 😀","Native WinHTTP gzip/Unicode failed");
            Require(response.Headers.GetValues("X-Msys2-Probe").Single()=="source","Native WinHTTP header lost");
        }
        using(var response=await client.GetAsync(new Uri(server.BaseUri,"missing")))
            Require(response.StatusCode==HttpStatusCode.NotFound && await response.Content.ReadAsStringAsync()=="missing","Native WinHTTP error response failed");
        using var cancel=new CancellationTokenSource(TimeSpan.FromMilliseconds(300));
        try { await client.GetAsync(new Uri(server.BaseUri,"slow"),cancel.Token); throw new Exception("Cancellation did not stop WinHTTP"); }
        catch(OperationCanceledException) when(cancel.IsCancellationRequested) { }
        Console.WriteLine("PASS: native WinHTTP loopback redirect, gzip, Unicode, headers, 404 and cancellation");
    }

    static async Task<int> Main()
    {
        RegistryAcl(); Dpapi(); Packaging(); Ldap(); await WinHttp();
        using var process=Process.GetCurrentProcess();
        foreach(ProcessModule module in process.Modules)
        {
            string path=module.FileName;
            Require(!path.Contains("\\Microsoft.NET\\Framework",StringComparison.OrdinalIgnoreCase),"Framework dependency loaded: "+path);
            if(new[]{"wldap32.dll","winhttp.dll","crypt32.dll","advapi32.dll"}.Contains(module.ModuleName,StringComparer.OrdinalIgnoreCase)) Console.WriteLine("NATIVE: "+path);
        }
        Console.WriteLine("PASS: all five source-built Windows library packages");
        return 0;
    }
}
