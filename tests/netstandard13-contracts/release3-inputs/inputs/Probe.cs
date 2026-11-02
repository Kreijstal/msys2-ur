using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
public static class Probe
{
    static async Task<int> Work(){return await Task.FromResult(42);}
    public static int Main()
    {
        System.Diagnostics.Debug.Fail("This call must be omitted from the Release consumer");
        var map=new Dictionary<string,int>(StringComparer.OrdinalIgnoreCase);map.Add("owned",42);
        if(map["OWNED"]!=42)return 1;
        byte[] data=Encoding.UTF8.GetBytes("Owned ✓");
        using(var stream=new MemoryStream(data))
        using(var reader=new StreamReader(stream,Encoding.UTF8))if(reader.ReadToEnd()!="Owned ✓")return 2;
        if(typeof(Probe).GetTypeInfo().DeclaredMethods==null || Marshal.SizeOf<int>()!=4)return 3;
        using(var cancellation=new CancellationTokenSource())
        {
            cancellation.Cancel();if(!cancellation.Token.IsCancellationRequested)return 4;
        }
        if(Work().GetAwaiter().GetResult()!=42)return 5;
        bool bad=false;try{map.Add("OWNED",0);}catch(ArgumentException){bad=true;}if(!bad)return 6;
        return 0;
    }
}
