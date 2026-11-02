using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;

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
    static void CodePagesChecks(bool windows)
    {
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
        int acp=(int)GetACP();var nativeDefault=provider.GetEncoding(0);Require(windows ? ((nativeDefault!=null && nativeDefault.CodePage==acp) || (nativeDefault==null && acp==65001)) : nativeDefault==null,"Original platform-specific default code page behavior");
        var tasks=new List<Task>();for(int i=0;i<12;i++)tasks.Add(Task.Run(()=>{for(int j=0;j<30;j++)Require(provider.GetEncoding(932).GetString(japanese.GetBytes("日本語"))=="日本語","Concurrent encoding cache");}));Task.WaitAll(tasks.ToArray());
    }
    public static string Run(bool windows){CodePagesChecks(windows);return "PASS exact legacy encoding bytes, multibyte/stateful round trips, fallbacks, streaming surrogate state, concurrency and original platform-specific ACP behavior";}
}
