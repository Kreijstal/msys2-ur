using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using Microsoft.Win32;
using Microsoft.Win32.SafeHandles;

public static class Bridge
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static bool Equal<T>(T[] left,T[] right)
    {
        if(left.Length!=right.Length)return false;
        for(int i=0;i<left.Length;i++)if(!EqualityComparer<T>.Default.Equals(left[i],right[i]))return false;
        return true;
    }
    [DllImport("kernel32.dll")]static extern uint GetACP();
    static void RegistryChecks()
    {
        Require(typeof(RegistryKey).GetTypeInfo().Assembly.GetName().Version.ToString()=="4.0.1.0","Must execute original Registry identity");
        foreach(var view in new[]{RegistryView.Registry32,RegistryView.Registry64})
        using(var machine=RegistryKey.OpenBaseKey(RegistryHive.LocalMachine,view))
        using(var version=machine.OpenSubKey(@"SOFTWARE\Microsoft\Windows NT\CurrentVersion"))
        {
            Require(version!=null && !string.IsNullOrEmpty((string)version.GetValue("ProductName")),"Native OS registry query "+view);
            Require(version.GetValueKind("ProductName")==RegistryValueKind.String,"Native value kind");
        }
        string relative=@"Software\CodexMsys2LegacyRegistry-"+Guid.NewGuid().ToString("N");
        try
        {
            using(var key=Registry.CurrentUser.CreateSubKey(relative))
            {
                key.SetValue("unicode","Owned ✓ 日本語",RegistryValueKind.String);
                key.SetValue("dword",42,RegistryValueKind.DWord);
                key.SetValue("qword",0x123456789abcL,RegistryValueKind.QWord);
                key.SetValue("binary",new byte[]{0,1,127,255},RegistryValueKind.Binary);
                key.SetValue("multi",new[]{"one","✓"},RegistryValueKind.MultiString);
                key.SetValue("expand","%SystemRoot%",RegistryValueKind.ExpandString);
                Require((string)key.GetValue("unicode")=="Owned ✓ 日本語" && (int)key.GetValue("dword")==42 && (long)key.GetValue("qword")==0x123456789abcL,"Native string/integer round trips");
                Require(Equal((byte[])key.GetValue("binary"),new byte[]{0,1,127,255}) && Equal((string[])key.GetValue("multi"),new[]{"one","✓"}),"Native binary/multistring round trips");
                Require((string)key.GetValue("expand",null,RegistryValueOptions.DoNotExpandEnvironmentNames)=="%SystemRoot%" && (string)key.GetValue("expand")==Environment.GetEnvironmentVariable("SystemRoot"),"Expandable strings");
                using(var child=key.CreateSubKey("OwnedChild"))child.SetValue("child",7);
                Require(Array.IndexOf(key.GetSubKeyNames(),"OwnedChild")>=0 && key.ValueCount==6 && key.GetValueNames().Length==6,"Native enumeration/counts");
                using(var child=key.OpenSubKey("OwnedChild"))Require((int)child.GetValue("child")==7,"Independent child handle");
                using(var borrowed=RegistryKey.FromHandle(new SafeRegistryHandle(key.Handle.DangerousGetHandle(),false)))Require((int)borrowed.GetValue("dword")==42,"Borrowed native handle");
                Require((int)key.GetValue("dword")==42,"Borrowed disposal must not close owner");
                key.DeleteValue("binary");Require(key.GetValue("binary")==null,"Native value deletion");
                key.DeleteSubKey("OwnedChild");Require(key.SubKeyCount==0,"Native child deletion");key.Flush();
            }
            using(var readOnly=Registry.CurrentUser.OpenSubKey(relative,false))
            {
                bool denied=false;try{readOnly.SetValue("denied",1);}catch(UnauthorizedAccessException){denied=true;}Require(denied,"Read-only access negative control");
            }
            Registry.SetValue(@"HKEY_CURRENT_USER\"+relative,"static",99,RegistryValueKind.DWord);
            Require((int)Registry.GetValue(@"HKEY_CURRENT_USER\"+relative,"static",null)==99,"Static native registry APIs");
            var disposed=Registry.CurrentUser.OpenSubKey(relative);disposed.Dispose();bool closed=false;
            try{disposed.GetValue("static");}catch(ObjectDisposedException){closed=true;}Require(closed,"Disposed key negative control");
        }
        finally{Registry.CurrentUser.DeleteSubKeyTree(relative,false);}
        using(var absent=Registry.CurrentUser.OpenSubKey(relative))Require(absent==null,"Owned registry subtree cleanup");
    }
    static void CodePagesChecks()
    {
        Require(typeof(CodePagesEncodingProvider).GetTypeInfo().Assembly.GetName().Version.ToString()=="4.0.1.0","Must execute original CodePages identity");
        var provider=CodePagesEncodingProvider.Instance;
        var western=provider.GetEncoding(1252);Require(Equal(western.GetBytes("€ café"),new byte[]{128,32,99,97,102,233}),"CP1252 exact bytes");
        Require(western.GetString(new byte[]{128,32,99,97,102,233})=="€ café","CP1252 decode");
        var japanese=provider.GetEncoding(932);Require(Equal(japanese.GetBytes("日本語"),new byte[]{147,250,150,123,140,234}),"Shift-JIS exact bytes");
        foreach(var item in new[]{Tuple.Create(437,"Grüße"),Tuple.Create(932,"日本語"),Tuple.Create(949,"한국어"),Tuple.Create(1361,"한국어"),Tuple.Create(50220,"日本語"),Tuple.Create(54936,"中文𐐷")})
        {
            var encoding=provider.GetEncoding(item.Item1);Require(encoding!=null && encoding.GetString(encoding.GetBytes(item.Item2))==item.Item2,"Legacy encoding round trip "+item.Item1);
        }
        Require(provider.GetEncoding("windows-1252").CodePage==1252 && provider.GetEncoding("shift_jis").CodePage==932,"IANA name lookup");
        Require(provider.GetEncoding("owned-unknown-encoding")==null && provider.GetEncoding(int.MaxValue)==null,"Unsupported encoding controls");
        var strict=provider.GetEncoding(932,EncoderFallback.ExceptionFallback,DecoderFallback.ExceptionFallback);
        bool rejected=false;try{strict.GetString(new byte[]{0x81});}catch(DecoderFallbackException){rejected=true;}Require(rejected,"Incomplete DBCS input");
        rejected=false;try{provider.GetEncoding(1252,EncoderFallback.ExceptionFallback,DecoderFallback.ExceptionFallback).GetBytes("𐐷");}catch(EncoderFallbackException){rejected=true;}Require(rejected,"Unrepresentable Unicode input");
        var gb=provider.GetEncoding(54936);var encoder=gb.GetEncoder();byte[] bytes=new byte[16];int charsUsed,bytesUsed;bool completed;
        encoder.Convert(new[]{'\ud801'},0,1,bytes,0,bytes.Length,false,out charsUsed,out bytesUsed,out completed);Require(charsUsed==1 && bytesUsed==0,"Streaming high surrogate state");
        encoder.Convert(new[]{'\udc37'},0,1,bytes,0,bytes.Length,true,out charsUsed,out bytesUsed,out completed);Require(completed && gb.GetString(bytes,0,bytesUsed)=="𐐷","Streaming supplementary round trip");
        int acp=(int)GetACP();var nativeDefault=provider.GetEncoding(0);Require((nativeDefault!=null && nativeDefault.CodePage==acp) || (nativeDefault==null && acp==65001),"Native active code page lookup");
        var tasks=new List<Task>();for(int i=0;i<12;i++)tasks.Add(Task.Run(()=>{for(int j=0;j<30;j++)Require(provider.GetEncoding(932).GetString(japanese.GetBytes("日本語"))=="日本語","Concurrent encoding cache");}));Task.WaitAll(tasks.ToArray());
    }
    public static string Run(){RegistryChecks();CodePagesChecks();return "PASS original Registry4.3 native OS/views/owned-key CRUD/handles/errors/cleanup and CodePages4.0.1 exact bytes/multibyte/stateful/fallback/concurrency/native-ACP checks";}
}
