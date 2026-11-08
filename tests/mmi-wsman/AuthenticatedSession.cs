using System;
using System.Collections.Concurrent;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Options;

static class AuthenticatedSession
{
    sealed class Settings
    {
        public string Host {get;set;}="";
        public uint Port {get;set;}=5986;
        public string Domain {get;set;}="";
        public string Username {get;set;}="";
        public string Password {get;set;}="";
        public string Namespace {get;set;}="root/cimv2";
        public string ClassName {get;set;}="Win32_OperatingSystem";
        public bool AllowUntrustedCertificate {get;set;}
        public bool TestInvalidPassword {get;set;}
    }
    static int checks;
    static void Require(bool condition,string message){Interlocked.Increment(ref checks);if(!condition)throw new InvalidOperationException(message);}
    static WSManSessionOptions Options(Settings settings,bool invalid=false)
    {
        using var password=new SecureString();
        foreach(char value in invalid?"invalid-"+Guid.NewGuid().ToString("N"):settings.Password)password.AppendChar(value);
        using var original=new WSManSessionOptions {
            DestinationPort=settings.Port,UseSsl=true,Timeout=TimeSpan.FromSeconds(20),
            CertCACheck=!settings.AllowUntrustedCertificate,CertCNCheck=!settings.AllowUntrustedCertificate,CertRevocationCheck=!settings.AllowUntrustedCertificate
        };
        original.AddDestinationCredentials(new CimCredential(PasswordAuthenticationMechanism.Negotiate,settings.Domain,settings.Username,password));
        var clone=new WSManSessionOptions(original);
        password.Clear();
        return clone;
    }
    static int Counter(string name)=>(int)typeof(CimSession).Assembly.GetType("Microsoft.Management.Infrastructure.Native.MI_OperationCallbackBridge",true).GetField(name,BindingFlags.Static|BindingFlags.NonPublic).GetValue(null);
    sealed class Observer:IObserver<CimInstance>,IDisposable
    {
        internal readonly ConcurrentQueue<CimInstance> Values=new();
        internal readonly ManualResetEventSlim Done=new();
        internal Exception Error;
        internal int Terminals;
        public void OnNext(CimInstance value){if(value!=null)Values.Enqueue(value);GC.Collect(2,GCCollectionMode.Forced,true,true);}
        public void OnError(Exception error){Error=error;Interlocked.Increment(ref Terminals);Done.Set();}
        public void OnCompleted(){Interlocked.Increment(ref Terminals);Done.Set();}
        public void Dispose(){foreach(var value in Values)value.Dispose();(Error as IDisposable)?.Dispose();Done.Dispose();}
    }
    static void Connection(CimSession session)
    {
        bool success=session.TestConnection(out var identity,out var error);
        try {Require(success&&error==null,"Authenticated WSMan TestConnection");Require(identity!=null,"Remote identity response");}
        finally {identity?.Dispose();(error as IDisposable)?.Dispose();}
    }
    static void Positive(Settings settings)
    {
        using var options=Options(settings);
        using var session=CimSession.Create(settings.Host,options);
        Connection(session);
        using(var cls=session.GetClass(settings.Namespace,settings.ClassName))
        {
            Require(cls.CimSystemProperties.ClassName.Equals(settings.ClassName,StringComparison.OrdinalIgnoreCase),"Authenticated remote class metadata");
            Require(cls.CimClassProperties.Count>0,"Remote class property metadata");
        }
        using var operationOptions=new CimOperationOptions {Timeout=TimeSpan.FromSeconds(20)};
        string query="SELECT * FROM "+settings.ClassName;
        int rows=0;
        using(var iterator=session.QueryInstances(settings.Namespace,"WQL",query,operationOptions).GetEnumerator())
        {
            while(iterator.MoveNext())
            {
                using var value=iterator.Current;
                Require(value.CimSystemProperties.ClassName.Equals(settings.ClassName,StringComparison.OrdinalIgnoreCase),"Remote query class");
                rows++;
                if(rows>=128)break;
            }
        }
        Require(rows>0,"Authenticated remote query rows");
        using var observer=new Observer();
        using var subscription=session.QueryInstancesAsync(settings.Namespace,"WQL",query,operationOptions).Subscribe(observer);
        Require(observer.Done.Wait(TimeSpan.FromSeconds(30)),"Authenticated remote asynchronous query completed");
        if(observer.Error!=null)throw observer.Error;
        Require(observer.Terminals==1&&!observer.Values.IsEmpty,"One async completion with remote values");
        subscription.Dispose();session.Close();
        Require(SpinWait.SpinUntil(()=>Counter("ActiveCount")==0,TimeSpan.FromSeconds(10)),"Remote callback roots released");
        Require(Counter("CleanupFailures")==0,"Remote native operation cleanup");
        GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();
        Require(observer.Values.All(value=>value.CimSystemProperties.ClassName.Equals(settings.ClassName,StringComparison.OrdinalIgnoreCase)),"Remote values survive session/operation close and GC");
        using var freshOptions=Options(settings);
        using var fresh=CimSession.Create(settings.Host,freshOptions);
        Connection(fresh);
    }
    static void InvalidPassword(Settings settings)
    {
        using var options=Options(settings,true);
        using var session=CimSession.Create(settings.Host,options);
        bool success=session.TestConnection(out var identity,out var error);
        try {Require(!success&&error!=null,"Incorrect password rejected");Require(error.NativeErrorCode==NativeErrorCode.AccessDenied,"Incorrect password rejected as authentication failure");}
        finally {identity?.Dispose();(error as IDisposable)?.Dispose();}
    }
    static void SelfCheck()
    {
        var settings=JsonSerializer.Deserialize<Settings>("{\"host\":\"localhost\",\"username\":\"source-fixture\",\"password\":\"dummy-credential-only\"}",new JsonSerializerOptions {PropertyNameCaseInsensitive=true});
        Require(settings!=null&&settings.Host=="localhost"&&settings.Namespace=="root/cimv2","Private JSON settings contract/defaults");
        using var options=Options(settings);
        Require(options.UseSsl&&options.DestinationPort==5986,"Cloned HTTPS destination settings");
        Require(options.CertCACheck&&options.CertCNCheck&&options.CertRevocationCheck,"Certificate verification enabled by default");
        const BindingFlags hidden=BindingFlags.Instance|BindingFlags.NonPublic;
        object native=typeof(CimSessionOptions).GetProperty("DestinationOptionsHandleOnDemand",hidden).GetValue(options);
        object[] count={0u};
        Require(Convert.ToUInt32(native.GetType().GetMethod("GetCredentialsCount",hidden).Invoke(native,count))==0&&(uint)count[0]==1,"Cloned native destination contains explicit credentials");
        var readPassword=native.GetType().GetMethod("GetCredentialsPasswordAt",hidden);
        object[] sizing={0u,null,IntPtr.Zero,0u,null,null};readPassword.Invoke(native,sizing);
        uint length=(uint)sizing[4];Require(length>0&&length<=4096,"Native credential password buffer size");
        IntPtr buffer=Marshal.AllocHGlobal(checked((int)length*2));
        try
        {
            object[] read={0u,null,buffer,length,null,null};
            Require(Convert.ToUInt32(readPassword.Invoke(native,read))==0,"Native credential password readback");
            Require(Marshal.PtrToStringUni(buffer)==settings.Password,"Native credentials survive password clearing and original option disposal");
        }
        finally {for(int i=0;i<checked((int)length*2);i++)Marshal.WriteByte(buffer,i,0);Marshal.FreeHGlobal(buffer);}
        settings.AllowUntrustedCertificate=true;
        using var scoped=Options(settings);
        Require(!scoped.CertCACheck&&!scoped.CertCNCheck&&!scoped.CertRevocationCheck,"Optional certificate bypass is confined to test options");
        Console.WriteLine("PASS "+checks+" offline WSMan settings/credential-copy/clone checks; no connection attempted");
    }
    static int Main(string[] args)
    {
        try
        {
            if(args.Length==1&&args[0]=="--self-check"){SelfCheck();return 0;}
            if(args.Length!=2)throw new ArgumentException("PRIVATE_SETTINGS_JSON RESULTS_JSON required");
            var settings=JsonSerializer.Deserialize<Settings>(File.ReadAllText(args[0]),new JsonSerializerOptions {PropertyNameCaseInsensitive=true})??throw new ArgumentException("Invalid settings");
            Require(Uri.CheckHostName(settings.Host)!=UriHostNameType.Unknown&&settings.Port>0&&settings.Port<=65535,"Endpoint hostname and port");
            Require(!string.IsNullOrWhiteSpace(settings.Username)&&settings.Password.Length>0,"Explicit credentials supplied");
            Require(Regex.IsMatch(settings.ClassName,"^[A-Za-z_][A-Za-z0-9_]*$")&&Regex.IsMatch(settings.Namespace,@"^[A-Za-z0-9_/\\]+$"),"Read-only query target identifiers");
            Positive(settings);
            if(settings.TestInvalidPassword)InvalidPassword(settings);
            var result=new {
                checks,passed=true,protocol="WSMan over HTTPS",authentication="Negotiate with explicit password credentials",
                endpointHash=Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(settings.Host+":"+settings.Port))),
                certificateChecksEnabled=!settings.AllowUntrustedCertificate,invalidPasswordTested=settings.TestInvalidPassword,
                MMI_DLL_sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(typeof(CimSession).Assembly.Location))),
                full_dependency_goal_complete=false
            };
            File.WriteAllText(args[1],JsonSerializer.Serialize(result,new JsonSerializerOptions {WriteIndented=true})+"\n");
            Console.WriteLine("PASS "+checks+" authenticated HTTPS/WSMan credential-clone/query/async/lifetime checks");return 0;
        }
        catch(Exception error)
        {
            // Native diagnostic text may include account or endpoint details.
            // Keep secrets and remote identifiers out of public console logs.
            Console.Error.WriteLine("Authenticated WSMan check failed: "+error.GetType().Name+(error is CimException cim?"; native code="+cim.NativeErrorCode:""));return 1;
        }
    }
}
