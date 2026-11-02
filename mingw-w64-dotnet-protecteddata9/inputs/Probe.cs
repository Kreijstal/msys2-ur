using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
internal static class Probe
{
    static void Require(bool condition,string message) { if(!condition)throw new Exception(message); }
    static void Native(string executable,string mode,string input,string output,string entropy,string scope)
    {
        var start=new ProcessStartInfo(executable){UseShellExecute=false};foreach(string arg in new[]{mode,input,output,entropy,scope})start.ArgumentList.Add(arg);
        using var process=Process.Start(start)!;Require(process.WaitForExit(15000)&&process.ExitCode==0,"Independent native DPAPI "+mode);
    }
    static int Main(string[] args)
    {
        string output=args[0],native=args[1];var assembly=typeof(ProtectedData).Assembly;
        Require(assembly.GetName().Version==new Version(9,0,0,0),"Original targeting-pack version");Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="b03f5f7f11d50a3a","Original Microsoft key");
        Require(assembly.GetCustomAttribute<TargetFrameworkAttribute>()?.FrameworkName==".NETCoreApp,Version=v9.0","Original NET9 target");Require(assembly.GetCustomAttribute<CLSCompliantAttribute>()?.IsCompliant==true,"Original CLS policy");Require(assembly.GetCustomAttribute<SupportedOSPlatformAttribute>()?.PlatformName=="windows","Original Windows support annotation");
        Require(Path.GetDirectoryName(assembly.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"Source library loaded from fresh consumer");
        var expected=JsonSerializer.Deserialize<Dictionary<string,string>>(File.ReadAllText(Path.Combine(output,"neutral-strings.json")))!;var manager=new ResourceManager("FxResources.System.Security.Cryptography.ProtectedData.SR",assembly);using var set=manager.GetResourceSet(CultureInfo.InvariantCulture,true,false)!;
        Require(set.Cast<DictionaryEntry>().Count()==expected.Count,"Original resource count");foreach(var pair in expected)Require(manager.GetString(pair.Key,CultureInfo.InvariantCulture)==pair.Value,"Original resource value:"+pair.Key);
        byte[] entropy=Encoding.UTF8.GetBytes("λ independent entropy 世界");int cases=0;
        foreach(var scope in new[]{DataProtectionScope.CurrentUser,DataProtectionScope.LocalMachine})
        foreach(byte[] data in new[]{Array.Empty<byte>(),Encoding.UTF8.GetBytes("λ Unicode payload 世界\0end"),Enumerable.Range(0,256).Select(i=>(byte)i).ToArray(),Enumerable.Range(0,65536).Select(i=>(byte)(i%251)).ToArray()})
        foreach(byte[]? extra in new byte[]?[]{null,Array.Empty<byte>(),entropy})
        {
            var saved=data.ToArray();byte[]? savedEntropy=extra?.ToArray();var encrypted=ProtectedData.Protect(data,extra,scope);Require(!encrypted.SequenceEqual(data),"Data encrypted");Require(ProtectedData.Unprotect(encrypted,extra,scope).SequenceEqual(data),"DPAPI roundtrip "+scope);Require(data.SequenceEqual(saved)&&(extra==null||extra.SequenceEqual(savedEntropy!)),"Caller input and entropy unmodified");cases++;
        }
        foreach(var scope in new[]{DataProtectionScope.CurrentUser,DataProtectionScope.LocalMachine})
        {
            string label=scope==DataProtectionScope.CurrentUser?"user":"machine";byte[] data=Encoding.UTF8.GetBytes("λ native ABI payload 世界");string input=Path.Combine(output,label+".input"),ent=Path.Combine(output,label+".entropy"),encrypted=Path.Combine(output,label+".native-encrypted"),plain=Path.Combine(output,label+".native-plain");File.WriteAllBytes(input,data);File.WriteAllBytes(ent,entropy);
            Native(native,"protect",input,encrypted,ent,label);Require(ProtectedData.Unprotect(File.ReadAllBytes(encrypted),entropy,scope).SequenceEqual(data),"Native protect/source unprotect");File.WriteAllBytes(encrypted,ProtectedData.Protect(data,entropy,scope));Native(native,"unprotect",encrypted,plain,ent,label);Require(File.ReadAllBytes(plain).SequenceEqual(data),"Source protect/native unprotect");
        }
        byte[] protectedValue=ProtectedData.Protect(new byte[]{1,2,3,4},entropy,DataProtectionScope.CurrentUser);bool wrongEntropy=false;try{ProtectedData.Unprotect(protectedValue,new byte[]{9},DataProtectionScope.CurrentUser);}catch(CryptographicException e){wrongEntropy=!string.IsNullOrWhiteSpace(e.Message);}Require(wrongEntropy,"Wrong entropy returns native crypto failure");protectedValue[protectedValue.Length/2]^=0x20;bool tampered=false;try{ProtectedData.Unprotect(protectedValue,entropy,DataProtectionScope.CurrentUser);}catch(CryptographicException){tampered=true;}Require(tampered,"Tampered ciphertext rejected");
        bool nullProtect=false,nullUnprotect=false;try{ProtectedData.Protect(null!,null,DataProtectionScope.CurrentUser);}catch(ArgumentNullException){nullProtect=true;}try{ProtectedData.Unprotect(null!,null,DataProtectionScope.CurrentUser);}catch(ArgumentNullException){nullUnprotect=true;}Require(nullProtect&&nullUnprotect,"Original null argument validation");
        var unknown=ProtectedData.Protect(new byte[]{7,8},null,(DataProtectionScope)123);Require(ProtectedData.Unprotect(unknown,null,DataProtectionScope.CurrentUser).SequenceEqual(new byte[]{7,8}),"Original unknown scope bits treated as CurrentUser");
        for(int i=0;i<40;i++){var value=ProtectedData.Protect(new byte[]{(byte)i},entropy,DataProtectionScope.CurrentUser);Require(ProtectedData.Unprotect(value,entropy,DataProtectionScope.CurrentUser)[0]==i,"Repeated native buffer lifecycle");if(i%10==0)GC.Collect(2,GCCollectionMode.Forced,true,true);}
        Console.WriteLine("PASS source ProtectedData9:"+cases+" user/machine Unicode/empty/binary/entropy roundtrips,4 independent native crosschecks,all"+expected.Count+" resources,error/null/scope compatibility and40 GC lifecycle iterations");return 0;
    }
}
