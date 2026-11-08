using System;
using System.Data.SqlClient;
using System.Diagnostics;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;

internal static class LocalDbChecks
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]private delegate void Reset(int mode);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]private delegate int Count();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]private delegate IntPtr Name();
    private static int checks;
    private static void Require(bool value,string message){checks++;if(!value)throw new Exception(message);}
    private static readonly BindingFlags Private=BindingFlags.NonPublic|BindingFlags.Public|BindingFlags.Instance|BindingFlags.Static;
    private static int Main(string[] args)
    {
        IntPtr library=IntPtr.Zero;SafeHandle handle=null;
        object singleton=null;FieldInfo libraryField=null,startField=null;object oldLibrary=null,oldStart=null;
        try
        {
            bool baseline=args.Contains("--baseline");
            var assembly=typeof(SqlConnection).Assembly;
            var type=assembly.GetType("System.Data.SqlClient.SNI.LocalDB",true);
            singleton=type.GetField("Instance",Private).GetValue(null);
            libraryField=type.GetField("_sqlUserInstanceLibraryHandle",Private);startField=type.GetField("localDBStartInstanceFunc",Private);
            oldLibrary=libraryField.GetValue(singleton);oldStart=startField.GetValue(singleton);
            library=NativeLibrary.Load(System.IO.Path.Combine(AppContext.BaseDirectory,"localdb-driver.dll"));
            var reset=Marshal.GetDelegateForFunctionPointer<Reset>(NativeLibrary.GetExport(library,"reset_driver"));
            var count=Marshal.GetDelegateForFunctionPointer<Count>(NativeLibrary.GetExport(library,"call_count"));
            var starts=Marshal.GetDelegateForFunctionPointer<Count>(NativeLibrary.GetExport(library,"start_count"));
            var name=Marshal.GetDelegateForFunctionPointer<Name>(NativeLibrary.GetExport(library,"instance_name"));
            handle=(SafeHandle)Activator.CreateInstance(libraryField.FieldType,true);
            typeof(SafeHandle).GetMethod("SetHandle",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(handle,new object[]{library});
            libraryField.SetValue(singleton,handle);
            startField.SetValue(singleton,Marshal.GetDelegateForFunctionPointer(NativeLibrary.GetExport(library,"LocalDBStartInstance"),startField.FieldType));
            var get=type.GetMethod("GetConnectionString",Private);
            var proxyType=assembly.GetType("System.Data.SqlClient.SNI.SNIProxy",true);
            var proxy=proxyType.GetField("Singleton",Private).GetValue(null);
            var lookup=proxyType.GetMethod("GetLocalDBDataSource",Private);
            reset(1);
            string failed=(string)get.Invoke(singleton,new object[]{"owned-雪"});
            if(baseline)Require(failed=="","Installed baseline ignores native failure HRESULT and returns empty pipe");
            else Require(failed==null,"Native startup failure returns no pipe");
            object[] lookupArgs={"(localdb)\\owned-雪",false};
            var route=lookup.Invoke(proxy,lookupArgs);
            if(baseline)Require(!(bool)lookupArgs[1],"Installed baseline fails to propagate LocalDB lookup failure flag");
            else Require(route==null&&(bool)lookupArgs[1],"LocalDB failure stops transport routing");
            Require(Marshal.PtrToStringUni(name())=="owned-雪","Native API receives Unicode instance name");
            if(baseline){Console.WriteLine("REPRODUCED ignored native HRESULT and lost LocalDB failure routing");return 0;}
            var load=assembly.GetType("System.Data.SqlClient.SNI.SNILoadHandle",true);
            var loadInstance=load.GetField("SingletonInstance",Private).GetValue(null);
            var error=load.GetProperty("LastError",Private).GetValue(loadInstance);
            Require((uint)error.GetType().GetField("nativeError").GetValue(error)==0x80004005u,"Native HRESULT retained");
            Require((uint)error.GetType().GetField("sniError").GetValue(error)==50,"LocalDB SNI error classification");
            reset(0);string pipe=(string)get.Invoke(singleton,new object[]{"owned-success"});
            Require(pipe=="np:\\\\.\\pipe\\msys2-localdb-owned\\tsql\\query","Successful native pipe returned exactly");
            Require(starts()==1&&count()>=1,"Exactly one native start with buffer negotiation");
            reset(2);string large=(string)get.Invoke(singleton,new object[]{"owned-long"});
            Require(large.Length==699&&large.All(c=>c=='x'),"Native requested buffer size honored");
            Require(starts()==1,"Size query does not start an instance");
            reset(5);large=(string)get.Invoke(singleton,new object[]{"owned-race"});
            Require(large.Length==699&&starts()==1&&count()==3,"Changed native buffer requirement retries without duplicate starts");
            reset(3);Require(get.Invoke(singleton,new object[]{"owned-empty"})==null,"Empty successful pipe is rejected");
            foreach(int invalidSize in new[]{6,7})
            {
                reset(invalidSize);Require(get.Invoke(singleton,new object[]{"owned-invalid-size"})==null,"Invalid native buffer size is rejected");
                Require(starts()==0&&count()==1,"Invalid size does not allocate/start an instance");
            }
            reset(8);Require(get.Invoke(singleton,new object[]{"owned-start-error"})==null,"Failure after size query returns no pipe");
            error=load.GetProperty("LastError",Private).GetValue(loadInstance);
            Require((uint)error.GetType().GetField("nativeError").GetValue(error)==0x80004005u&&starts()==1,"Post-query start HRESULT retained");
            reset(9);Require(get.Invoke(singleton,new object[]{"owned-growing"})==null,"Repeated native size changes fail after bounded retries");
            Require(count()==4&&starts()==0,"One query and three bounded buffer attempts");
            error=load.GetProperty("LastError",Private).GetValue(loadInstance);
            Require((uint)error.GetType().GetField("nativeError").GetValue(error)==0x89c50114u,"Insufficient-buffer HRESULT retained after bounded retries");
            reset(1);
            using var connection=new SqlConnection("Data Source=(localdb)\\owned-public;Integrated Security=true;Connect Timeout=1;Pooling=false");
            bool publicFailure=false;
            try{connection.Open();}
            catch(SqlException exception){Require(exception.Number==unchecked((int)0x80004005u),"Public SqlException retains native HRESULT");Require(exception.Message.Contains("Owned LocalDB startup failure 雪"),"Public managed-SNI error uses native LocalDB Unicode formatter");publicFailure=true;Console.WriteLine("PUBLIC_LOCALDB_ERROR "+exception.Number);}
            Require(publicFailure&&Marshal.PtrToStringUni(name())=="owned-public","Public SqlConnection surfaces LocalDB failure without TCP fallback");
            reset(1);
            using(var asyncConnection=new SqlConnection("Data Source=(localdb)\\owned-async;Integrated Security=true;Connect Timeout=1;Pooling=false"))
            {
                bool asyncFailure=false;
                try {asyncConnection.OpenAsync().GetAwaiter().GetResult();}
                catch(SqlException errorAsync){asyncFailure=errorAsync.Number==unchecked((int)0x80004005u)&&errorAsync.Message.Contains("Owned LocalDB startup failure 雪");}
                Require(asyncFailure&&Marshal.PtrToStringUni(name())=="owned-async","OpenAsync preserves native LocalDB failure and Unicode message");
            }
            Require(System.IO.Path.GetFullPath(assembly.Location).StartsWith(System.IO.Path.GetFullPath(AppContext.BaseDirectory),StringComparison.OrdinalIgnoreCase),"Source consumer loads its private restored implementation");
            using(var process=Process.GetCurrentProcess())
                Require(!process.Modules.Cast<ProcessModule>().Any(module=>module.ModuleName.Equals("sni.dll",StringComparison.OrdinalIgnoreCase)||module.FileName.Contains("\\Microsoft.NET\\Framework",StringComparison.OrdinalIgnoreCase)),"No proprietary SNI or Framework helper loaded");
            Console.WriteLine("PASS "+checks+" LocalDB native ABI/HRESULT/buffer/Unicode/routing/public-error checks");return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
        finally
        {
            if(libraryField!=null)libraryField.SetValue(singleton,oldLibrary);
            if(startField!=null)startField.SetValue(singleton,oldStart);
            if(handle!=null){handle.SetHandleAsInvalid();handle.Dispose();}
            if(library!=IntPtr.Zero)NativeLibrary.Free(library);
        }
    }
}
