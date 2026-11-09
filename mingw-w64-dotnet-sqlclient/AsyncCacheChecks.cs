// Internal async-start/write-continuation state publication regression. This
// does not promise that callers may execute one SqlCommand concurrently.
using System;
using System.Data.SqlClient;
using System.Reflection;
using System.Threading;

internal static class AsyncCacheChecks
{
    public static int Run(string[] args)
    {
        try
        {
            bool baseline=Array.IndexOf(args,"--baseline")>=0;int splits=0,lost=0;
            var property=typeof(SqlCommand).GetProperty("cachedAsyncState",BindingFlags.Instance|BindingFlags.NonPublic);
            Type type=property.PropertyType;
            var end=type.GetField("_cachedEndMethod",BindingFlags.Instance|BindingFlags.NonPublic);
            var options=type.GetField("_cachedSetOptions",BindingFlags.Instance|BindingFlags.NonPublic);
            using(var warm=new SqlCommand())property.GetValue(warm);
            for(int i=0;i<1024;i++)
            {
                using var command=new SqlCommand();using var gate=new Barrier(3);
                object first=null,second=null;Exception failure=null;
                var a=new Thread(()=>{try{gate.SignalAndWait();first=property.GetValue(command);end.SetValue(first,"EndExecuteReader");}catch(Exception e){failure=e;}});
                var b=new Thread(()=>{try{gate.SignalAndWait();second=property.GetValue(command);options.SetValue(second,"owned options");}catch(Exception e){failure=e;}});
                a.Start();b.Start();gate.SignalAndWait();a.Join();b.Join();if(failure!=null)throw failure;
                object final=property.GetValue(command);
                if(!ReferenceEquals(first,second)||!ReferenceEquals(first,final))splits++;
                if(!Equals(end.GetValue(final),"EndExecuteReader")||!Equals(options.GetValue(final),"owned options"))lost++;
            }
            Console.WriteLine((baseline?"REPRODUCED":"PASS")+" async-cache checks=1024 splits="+splits+" lost="+lost);
            return baseline ? (splits>0&&lost>0?0:1) : (splits==0&&lost==0?0:1);
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
    static int Main(string[] args)=>Run(args);
}
