using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Management;
using System.Runtime.InteropServices;
using System.Threading;

internal static class PortChecks
{
    static void Require(bool condition,string message){if(!condition)throw new Exception(message);}
    internal static void Run()
    {
        Metadata();Methods();AsyncQuery();Events();Privileges();Backend();
    }
    static void Metadata()
    {
        using var process=new ManagementClass("Win32_Process");process.Get();
        Require(process.Properties["ProcessId"].Type==CimType.UInt32,"CIM property type");
        Require(!string.IsNullOrEmpty(process.Properties["ProcessId"].Origin),"property origin");
        Require(Convert.ToBoolean(process.Properties["Handle"].Qualifiers["Key"].Value),"key qualifier");
        Require(process.Methods["GetOwner"].OutParameters.Properties["User"].Type==CimType.String,"method signature");
        Require(process.Methods.Cast<MethodData>().Any(m=>m.Name=="GetOwner"),"method enumeration");
        using var clone=(ManagementClass)process.Clone();
        Require(clone.CompareTo(process,ComparisonSettings.IgnoreObjectSource),"object clone/compare");
        Require(process.GetText(TextFormat.Mof).Contains("Win32_Process"),"MOF object text");
        using var child=process.Derive("MSYS2_MemoryOnly_"+Guid.NewGuid().ToString("N"));
        child.Properties.Add("Fixture",CimType.String,false);child.Properties["Fixture"].Value="property λ";
        child.Properties["Fixture"].Qualifiers.Add("Description","qualifier λ");
        Require((string)child.Properties["Fixture"].Value=="property λ","in-memory property write");
        Require((string)child.Properties["Fixture"].Qualifiers["Description"].Value=="qualifier λ","in-memory qualifier write");
        child.Methods.Add("FixtureMethod",null,process.Methods["GetOwner"].OutParameters);
        child.Methods["FixtureMethod"].Qualifiers.Add("Description","method λ");
        Require((string)child.Methods["FixtureMethod"].Qualifiers["Description"].Value=="method λ","method qualifier");
        Require(!string.IsNullOrEmpty(child.Methods["FixtureMethod"].Origin),"method origin");
        child.Methods["FixtureMethod"].Qualifiers.Remove("Description");
        child.Methods.Remove("FixtureMethod");
        child.Properties["Fixture"].Qualifiers.Remove("Description");child.Properties.Remove("Fixture");
        Console.WriteLine("PASS WMI metadata/types/origins, qualifier and method enumeration, clone/compare/MOF, in-memory class/property/method/qualifier edits; no repository writes");
    }
    static void Methods()
    {
        using var process=new ManagementObject("Win32_Process.Handle='"+Environment.ProcessId+"'");
        using var result=process.InvokeMethod("GetOwner",null,null);
        Require(Convert.ToUInt32(result["ReturnValue"])==0&&!string.IsNullOrWhiteSpace(result["User"]?.ToString()),"GetOwner method invocation");
        using var searcher=new ManagementObjectSearcher("root\\cimv2","SELECT ProcessId FROM Win32_Process WHERE ProcessId="+Environment.ProcessId);
        using var collection=searcher.Get();
        using var first=collection.GetEnumerator();Require(first.MoveNext(),"first enumeration");
        using var second=collection.GetEnumerator();Require(second.MoveNext(),"cloned enumerator");
        using var left=(ManagementObject)first.Current;using var right=(ManagementObject)second.Current;
        Require(Convert.ToUInt32(left["ProcessId"])==Convert.ToUInt32(right["ProcessId"]),"independent enumerator clone");
        Console.WriteLine("PASS WMI native GetOwner method invocation and independent enumerator clones");
    }
    static void AsyncQuery()
    {
        using var completed=new ManualResetEventSlim();
        var observer=new ManagementOperationObserver();
        int count=0;ManagementStatus status=ManagementStatus.Failed;Exception failure=null;
        observer.ObjectReady+=(_,args)=>{
            try {using var value=args.NewObject;Require(Convert.ToUInt32(value["ProcessId"])==Environment.ProcessId,"async object value");Interlocked.Increment(ref count);}
            catch(Exception error){failure=error;}
        };
        observer.Completed+=(_,args)=>{status=args.Status;completed.Set();};
        using var searcher=new ManagementObjectSearcher("root\\cimv2","SELECT ProcessId FROM Win32_Process WHERE ProcessId="+Environment.ProcessId);
        searcher.Get(observer);
        GC.Collect(GC.MaxGeneration,GCCollectionMode.Forced,true,true);
        Require(completed.Wait(TimeSpan.FromSeconds(20)),"async query completion");
        if(failure!=null)throw failure;
        Require(status==ManagementStatus.NoError&&count==1,"async query status/count: "+status+"/"+count);
        Console.WriteLine("PASS WMI native asynchronous sink delivery/completion and compacting GC");
    }
    static void Events()
    {
        using var arrived=new ManualResetEventSlim();
        using var watcher=new ManagementEventWatcher("SELECT * FROM Win32_ProcessStartTrace WHERE ParentProcessID="+Environment.ProcessId);
        uint observed=0;Exception failure=null;
        watcher.EventArrived+=(_,args)=>{
            try {using var value=args.NewEvent;observed=Convert.ToUInt32(value["ProcessID"]);arrived.Set();}
            catch(Exception error){failure=error;arrived.Set();}
        };
        watcher.Start();
        try
        {
            using var child=Process.Start(new ProcessStartInfo("cmd.exe","/d /c exit 0"){UseShellExecute=false,CreateNoWindow=true});
            Require(arrived.Wait(TimeSpan.FromSeconds(20)),"process event delivery");
            if(failure!=null)throw failure;
            Require(observed==child.Id,"process event PID");
            child.WaitForExit();
        }
        finally {watcher.Stop();}
        Console.WriteLine("PASS WMI native process event callback, owned child PID and subscription cancellation");
    }
    static void Privileges()
    {
        using var identity=System.Security.Principal.WindowsIdentity.GetCurrent();
        var scope=new ManagementScope("root\\cimv2",new ConnectionOptions{EnablePrivileges=true});scope.Connect();
        using var searcher=new ManagementObjectSearcher(scope,new ObjectQuery("SELECT BuildNumber FROM Win32_OperatingSystem"));
        using var results=searcher.Get();Require(results.Count==1,"privileged scope query");
        using var after=System.Security.Principal.WindowsIdentity.GetCurrent();
        Require(identity.User==after.User,"thread identity restored");
        using var thread=System.Security.Principal.WindowsIdentity.GetCurrent(true);
        Require(thread==null,"temporary impersonation token removed");
        Console.WriteLine("PASS WMI EnablePrivileges query and restored thread identity");
    }
    [UnmanagedFunctionPointer(CallingConvention.Winapi)]delegate int Version();
    [UnmanagedFunctionPointer(CallingConvention.Winapi)]delegate int SetSecurity(ref bool reset,ref IntPtr handle);
    [UnmanagedFunctionPointer(CallingConvention.Winapi)]delegate int ResetSecurity(IntPtr handle);
    [UnmanagedFunctionPointer(CallingConvention.Winapi)]delegate IntPtr ErrorInfo();
    [UnmanagedFunctionPointer(CallingConvention.Winapi)]delegate int Get(int slot,IntPtr instance,[MarshalAs(UnmanagedType.LPWStr)]string property,int flags,IntPtr value,IntPtr type,IntPtr flavor);
    static void Backend()
    {
        string path=Process.GetCurrentProcess().Modules.Cast<ProcessModule>().Single(m=>m.ModuleName.Equals("msys-wmi-native.dll",StringComparison.OrdinalIgnoreCase)).FileName;
        string relative=System.IO.Path.GetRelativePath(AppContext.BaseDirectory,path).Replace(System.IO.Path.DirectorySeparatorChar,'/');
        Require(relative=="msys-wmi-native.dll"||relative=="runtimes/win-x64/native/msys-wmi-native.dll","native implementation location");
        IntPtr module=NativeLibrary.Load(path);
        try
        {
            Require(Marshal.GetDelegateForFunctionPointer<Version>(NativeLibrary.GetExport(module,"WmiPortAbiVersion"))()==1,"backend ABI version");
            var get=Marshal.GetDelegateForFunctionPointer<Get>(NativeLibrary.GetExport(module,"Get"));
            Require(get(4,IntPtr.Zero,null,0,IntPtr.Zero,IntPtr.Zero,IntPtr.Zero)==unchecked((int)0x80004003),"native null-pointer rejection");
            Require(get(999,new IntPtr(1),null,0,IntPtr.Zero,IntPtr.Zero,IntPtr.Zero)==unchecked((int)0x80070057),"native vtable-slot validation before pointer access");
            int error=Marshal.GetHRForException(new InvalidOperationException("native error fixture λ"));
            var getError=Marshal.GetDelegateForFunctionPointer<ErrorInfo>(NativeLibrary.GetExport(module,"WmiGetErrorInfo"));
            IntPtr info=getError();Require(info!=IntPtr.Zero,"native COM error info");
            try {Require(Marshal.GetExceptionForHR(error,info).Message.Contains("native error fixture λ"),"COM error message ownership");}
            finally {Marshal.Release(info);}
            var set=Marshal.GetDelegateForFunctionPointer<SetSecurity>(NativeLibrary.GetExport(module,"SetSecurity"));
            var reset=Marshal.GetDelegateForFunctionPointer<ResetSecurity>(NativeLibrary.GetExport(module,"ResetSecurity"));
            bool required=false;IntPtr state=IntPtr.Zero;
            Require(set(ref required,ref state)==0&&required&&state!=IntPtr.Zero,"temporary native token setup");
            try {using var token=System.Security.Principal.WindowsIdentity.GetCurrent(true);Require(token!=null,"temporary thread token exists");}
            finally {Require(reset(state)==0,"temporary token reset");}
            using var after=System.Security.Principal.WindowsIdentity.GetCurrent(true);
            Require(after==null,"native token reset restores no-impersonation state");
        }
        finally {NativeLibrary.Free(module);}
        foreach(ProcessModule loaded in Process.GetCurrentProcess().Modules)
            if(loaded.ModuleName.Equals("msys-wmi-native.dll",StringComparison.OrdinalIgnoreCase))
            {Console.WriteLine("Source-built WMI backend: "+loaded.FileName);Console.WriteLine("PASS native WMI ABI/null-pointer validation and temporary privilege token setup/reset");return;}
        throw new Exception("native WMI backend module not loaded");
    }
}
