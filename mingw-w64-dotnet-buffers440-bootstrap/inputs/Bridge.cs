using System;
using System.Buffers;
using System.Collections.Generic;
using System.Diagnostics.Tracing;
using System.Threading;
public static class Bridge
{
    static void Require(bool condition,string message){if(!condition)throw new Exception(message);}
    static void Throws<T>(Action action,string name) where T:ArgumentException
    {
        try{action();}catch(T error){Require(error.ParamName==name,"exception parameter "+name);return;}
        throw new Exception("Expected "+typeof(T).Name+" for "+name);
    }
    sealed class Listener:EventListener
    {
        public int Rented,Allocated,Returned,Errors;
        public string Error="";
        protected override void OnEventSourceCreated(EventSource source)
        {
            if(source.GetType().Assembly==typeof(ArrayPool<byte>).Assembly)EnableEvents(source,EventLevel.Verbose);
        }
        protected override void OnEventWritten(EventWrittenEventArgs data)
        {
            if(data.EventId==0){Interlocked.Increment(ref Errors);Error=data.Payload==null?"":string.Join(",",data.Payload);}
            if(data.EventId==1){Require(data.Payload.Count==4,"rent payload");Interlocked.Increment(ref Rented);}
            if(data.EventId==2){Require(data.Payload.Count==5,"allocation payload");Interlocked.Increment(ref Allocated);}
            if(data.EventId==3){Require(data.Payload.Count==3,"return payload");Interlocked.Increment(ref Returned);}
        }
    }
    public static string Events()
    {
        using(var listener=new Listener())
        {
            var pool=ArrayPool<byte>.Create(64,1);var array=pool.Rent(16);pool.Return(array);
            Require(listener.Errors==0,"source EventSource error: "+listener.Error);
            Require(listener.Rented==1 && listener.Allocated==1 && listener.Returned==1,"old implementation event delivery");
        }
        return "PASS exact old pool EventSource rent/allocation/return payload delivery";
    }
    public static string Run()
    {
        Require(typeof(ArrayPool<byte>).Assembly.GetName().Version.ToString()=="4.0.2.0","exact Buffers4.4 identity");
        Require(object.ReferenceEquals(ArrayPool<byte>.Shared,ArrayPool<byte>.Shared),"shared singleton");
        Require(!object.ReferenceEquals(ArrayPool<byte>.Create(),ArrayPool<byte>.Create()),"independent pools");
        Throws<ArgumentOutOfRangeException>(()=>ArrayPool<byte>.Create(0,1),"maxArrayLength");
        Throws<ArgumentOutOfRangeException>(()=>ArrayPool<byte>.Create(-1,1),"maxArrayLength");
        Throws<ArgumentOutOfRangeException>(()=>ArrayPool<byte>.Create(16,0),"maxArraysPerBucket");
        Throws<ArgumentOutOfRangeException>(()=>ArrayPool<byte>.Create(16,-1),"maxArraysPerBucket");
        var pool=ArrayPool<byte>.Create(64,1);
        Throws<ArgumentOutOfRangeException>(()=>pool.Rent(-1),"minimumLength");
        Throws<ArgumentNullException>(()=>pool.Return(null),"array");
        Throws<ArgumentException>(()=>pool.Return(new byte[17]),"array");
        var empty=pool.Rent(0);Require(empty.Length==0 && object.ReferenceEquals(empty,pool.Rent(0)),"zero singleton");pool.Return(empty);
        foreach(int size in new[]{1,15,16,17,31,32,33,63,64,65,127})
        {
            var first=pool.Rent(size);Require(first.Length>=size,"minimum size");pool.Return(first);
        }
        var owned=pool.Rent(64);owned[0]=42;owned[63]=84;pool.Return(owned,true);
        var again=pool.Rent(64);Require(object.ReferenceEquals(owned,again) && again[0]==0 && again[63]==0,"reuse and clear complete buffer");pool.Return(again);
        var refs=ArrayPool<object>.Create(16,1);var objects=refs.Rent(1);objects[0]=new object();refs.Return(objects,true);var clean=refs.Rent(1);Require(clean[0]==null,"reference clearing");refs.Return(clean);
        var large=pool.Rent(100);Require(large.Length==100,"over-limit allocation exact size");pool.Return(large);Require(!object.ReferenceEquals(large,pool.Rent(100)),"over-limit buffer is dropped");
        var exhausted=ArrayPool<int>.Create(16,1);var one=exhausted.Rent(16);var two=exhausted.Rent(16);Require(!object.ReferenceEquals(one,two),"exhausted bucket independent buffers");exhausted.Return(one);exhausted.Return(two);
        var concurrent=ArrayPool<int>.Create(1024,8);var threads=new Thread[8];Exception failure=null;
        for(int i=0;i<threads.Length;i++)
        {
            int marker=i+1;threads[i]=new Thread(()=>
            {
                try{for(int j=0;j<1000;j++){var a=concurrent.Rent(128);for(int k=0;k<128;k++)a[k]=marker;Thread.Yield();for(int k=0;k<128;k++)Require(a[k]==marker,"concurrent buffer ownership");concurrent.Return(a,true);}}
                catch(Exception error){Interlocked.CompareExchange(ref failure,error,null);}
            });threads[i].Start();
        }
        foreach(var thread in threads)thread.Join();if(failure!=null)throw failure;
        return "PASS original pool API, boundary sizes, exact argument errors/resource text, reuse/clearing, exhaustion/over-limit policy and 8000 concurrent rent/return ownership checks";
    }
}
