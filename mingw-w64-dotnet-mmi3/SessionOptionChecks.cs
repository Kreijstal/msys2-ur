using System;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Globalization;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Options;
using Microsoft.Management.Infrastructure.Native;
internal static class SessionOptionChecks
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl,CharSet=CharSet.Unicode)] delegate uint ReadNumber(IntPtr options,string name,out uint value);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl,CharSet=CharSet.Unicode)] delegate uint WriteNumber(IntPtr options,string name,uint value);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl,CharSet=CharSet.Unicode)] delegate uint ReadString(IntPtr options,string name,out IntPtr value);
    static ReadNumber readNumber;static WriteNumber writeNumber;static ReadString readString;
    static int checks,wrongSpn,leaks;
    const string Prefix="__MI_DESTINATIONOPTIONS_";
    static readonly FieldInfo Allocation=typeof(MI_NativeObject).GetField("allocatedData",BindingFlags.Instance|BindingFlags.NonPublic);
    static void Require(bool value,string message){checks++;if(!value)throw new Exception(message);}
    static void Spn(bool value,bool expected,bool baseline){if(value!=expected){wrongSpn++;if(!baseline)throw new Exception("SPN option getter reads a different native setting");}checks++;}
    static uint Number(WSManSessionOptions options,string key){Require(readNumber(options.DestinationOptionsHandleOnDemand.Ptr,Prefix+key,out var value)==0,"Native number read "+key);return value;}
    static string Text(WSManSessionOptions options,string key){Require(readString(options.DestinationOptionsHandleOnDemand.Ptr,Prefix+key,out var value)==0,"Native string read "+key);return Marshal.PtrToStringUni(value);}
    static void Closed(MI_NativeObject handle,bool baseline)
    {
        bool leaked=(IntPtr)Allocation.GetValue(handle)!=IntPtr.Zero;
        if(leaked){leaks++;Require(baseline,"Disposed public options retain unmanaged wrapper allocation");handle.Dispose();}
        else Require(!baseline,"Expected installed baseline wrapper leak");
        Require((IntPtr)Allocation.GetValue(handle)==IntPtr.Zero,"Wrapper allocation released exactly once");handle.Dispose();
    }
    static void Matrix(bool baseline)
    {
        for(int mask=0;mask<64;mask++)
        {
            var options=new WSManSessionOptions();
            bool ca=(mask&1)!=0,cn=(mask&2)!=0,rev=(mask&4)!=0,ssl=(mask&8)!=0,noEncryption=(mask&16)!=0,spn=(mask&32)!=0;
            options.CertCACheck=ca;options.CertCNCheck=cn;options.CertRevocationCheck=rev;options.UseSsl=ssl;options.NoEncryption=noEncryption;options.EncodePortInServicePrincipalName=spn;
            Require(options.CertCACheck==ca&&options.CertCNCheck==cn&&options.CertRevocationCheck==rev&&options.UseSsl==ssl&&options.NoEncryption==noEncryption,"Independent public option values");Spn(options.EncodePortInServicePrincipalName,spn,baseline);
            Require(Number(options,"CERT_CA_CHECK")==Convert.ToUInt32(ca),"CA native option");
            Require(Number(options,"CERT_CN_CHECK")==Convert.ToUInt32(cn),"CN native option");
            Require(Number(options,"CERT_REVOCATION_CHECK")==Convert.ToUInt32(rev),"Revocation native option");
            Require(Number(options,"PACKET_PRIVACY")==Convert.ToUInt32(!noEncryption),"Native encryption inversion");
            Require(Number(options,"ENCODE_PORT_IN_SPN")==Convert.ToUInt32(spn),"SPN native option");
            Require(Text(options,"TRANSPORT")== (ssl?"HTTPS":"HTTP"),"Native transport setting");
            Require(writeNumber(options.DestinationOptionsHandleOnDemand.Ptr,Prefix+"ENCODE_PORT_IN_SPN",Convert.ToUInt32(!spn))==0,"Independent native SPN mutation");
            Spn(options.EncodePortInServicePrincipalName,!spn,baseline);
            Require(options.CertRevocationCheck==rev,"SPN mutation preserves certificate revocation setting");
            var handle=options.DestinationOptionsHandleOnDemand;options.Dispose();options.Dispose();Closed(handle,baseline);
            bool disposed=false;try{_ = options.CertCACheck;}catch(ObjectDisposedException){disposed=true;}Require(disposed,"Disposed options reject access");
        }
    }
    static void CloneAndValues(bool baseline)
    {
        var original=new WSManSessionOptions{DestinationPort=5986,MaxEnvelopeSize=1024*1024,PacketEncoding=PacketEncoding.Utf16,ProxyType=ProxyType.WinHttp,UseSsl=true,EncodePortInServicePrincipalName=true,CertRevocationCheck=false,Timeout=TimeSpan.FromMilliseconds(123456),Culture=CultureInfo.GetCultureInfo("ja-JP"),UICulture=CultureInfo.GetCultureInfo("de-DE"),HttpUrlPrefix=new Uri("custom-wsman",UriKind.Relative)};
        var originalHandle=original.DestinationOptionsHandleOnDemand;
        var clone=new WSManSessionOptions(original);var cloneHandle=clone.DestinationOptionsHandleOnDemand;
        original.Dispose();Closed(originalHandle,baseline);
        Require(clone.DestinationPort==5986&&Number(clone,"DESTINATION_PORT")==5986,"Cloned destination port");
        Require(clone.MaxEnvelopeSize==1024*1024&&Number(clone,"MAX_ENVELOPE_SIZE")==1024*1024,"Cloned envelope size");
        Require(clone.PacketEncoding==PacketEncoding.Utf16&&Text(clone,"PACKET_ENCODING")=="UTF16","Cloned encoding");
        Require(clone.ProxyType==ProxyType.WinHttp&&Text(clone,"PROXY_TYPE")=="WinHTTP","Cloned proxy");
        Require(clone.Timeout==TimeSpan.FromMilliseconds(123456),"Cloned native interval");
        Require(clone.Culture.Name=="ja-JP"&&Text(clone,"DATA_LOCALE")=="ja-JP","Cloned culture");
        Require(clone.UICulture.Name=="de-DE"&&Text(clone,"UI_LOCALE")=="de-DE","Cloned UI culture");
        Require(clone.HttpUrlPrefix.ToString()=="custom-wsman"&&Text(clone,"HTTP_URL_PREFIX")=="custom-wsman","Cloned URL prefix");
        Require(Number(clone,"ENCODE_PORT_IN_SPN")==1&&Number(clone,"CERT_REVOCATION_CHECK")==0,"Clone preserves independent SPN/revocation storage");
        foreach(var encoding in new[]{PacketEncoding.Default,PacketEncoding.Utf8,PacketEncoding.Utf16}){clone.PacketEncoding=encoding;Require(clone.PacketEncoding==encoding,"Encoding round trip");}
        foreach(var proxy in new[]{ProxyType.None,ProxyType.Auto,ProxyType.InternetExplorer,ProxyType.WinHttp}){clone.ProxyType=proxy;Require(clone.ProxyType==proxy,"Proxy round trip");}
        clone.Dispose();clone.Dispose();Closed(cloneHandle,baseline);
        var baseOptions=new CimSessionOptions{Timeout=TimeSpan.FromSeconds(1)};var baseHandle=baseOptions.DestinationOptionsHandleOnDemand;baseOptions.Dispose();Closed(baseHandle,baseline);
        var dcom=new DComSessionOptions{PacketIntegrity=true,PacketPrivacy=true,Impersonation=ImpersonationType.Impersonate};var dcomHandle=dcom.DestinationOptionsHandleOnDemand;dcom.Dispose();Closed(dcomHandle,baseline);
        var operation=new CimOperationOptions{Timeout=TimeSpan.FromMilliseconds(4567)};var opHandle=operation.OperationOptionsHandle;operation.Dispose();operation.Dispose();Closed(opHandle,baseline);
        using var untouched=new CimSessionOptions();Require(untouched.DestinationOptionsHandle==null,"Untouched options allocate no native handle");
    }
    private static int Main(string[] args)
    {
        bool baseline=Array.IndexOf(args,"--baseline")>=0;IntPtr library=IntPtr.Zero;
        try
        {
            library=NativeLibrary.Load(System.IO.Path.Combine(AppContext.BaseDirectory,"session-options-native.dll"));
            readNumber=Marshal.GetDelegateForFunctionPointer<ReadNumber>(NativeLibrary.GetExport(library,"read_number"));writeNumber=Marshal.GetDelegateForFunctionPointer<WriteNumber>(NativeLibrary.GetExport(library,"write_number"));readString=Marshal.GetDelegateForFunctionPointer<ReadString>(NativeLibrary.GetExport(library,"read_string"));
            Matrix(baseline);CloneAndValues(baseline);
            Require(wrongSpn==(baseline?64:0),"Expected SPN mismatch count");Require(leaks==(baseline?69:0),"Expected native wrapper leak count");
            Console.WriteLine((baseline?"REPRODUCED":"PASS")+" session options checks="+checks+" SPN-mismatches="+wrongSpn+" wrapper-leaks="+leaks+" matrix=64");return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
        finally{if(library!=IntPtr.Zero)NativeLibrary.Free(library);}
    }
}
