using System;
using System.IO;
using System.Reflection;
using System.Runtime.CompilerServices;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Options;
internal static class Identity
{
    [ModuleInitializer]internal static void Check()
    {
        var assembly=typeof(CimSession).Assembly;
        if(assembly.GetName().Version!=new Version(1,0,0,0)||Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()!="31bf3856ad364e35")throw new Exception("MMI3 contract identity");
        if(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>().Version!="3.0.0.0"||assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion!="3.0.0-msys2-source-port+cf32fc695b32c2eae848b693395c09222fe1d2ae")throw new Exception("MMI3 port provenance");
        if(Path.GetDirectoryName(assembly.Location)!=Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location))throw new Exception("MMI3 consumer DLL location");
        if((long)CimFlags.Adopt!=2147483648L||Enum.GetUnderlyingType(typeof(ImpersonationType))!=typeof(int))throw new Exception("MMI3 enum contract");
        using var instance=new CimInstance("MsysMmiFriendContract");
        FriendSma.Validate(instance);FriendCimCmdlets.Validate(instance);
        Console.WriteLine("PASS MMI3 source-port identity/version/location, corrected enum contracts and signed friend access used by PowerShell sources");
    }
}
