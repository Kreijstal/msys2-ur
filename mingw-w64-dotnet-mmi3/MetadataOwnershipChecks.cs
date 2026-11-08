using System;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Native;

static class MetadataOwnershipChecks
{
    static int checks;
    static readonly FieldInfo Allocation = typeof(MI_NativeObject).GetField("allocatedData", BindingFlags.Instance | BindingFlags.NonPublic);
    static void Require(bool condition, string message) { checks++; if (!condition) throw new Exception(message); }
    static MI_NativeObject NewView(int kind, IntPtr borrowed) => kind switch {
        0 => MI_QualifierSet.NewDirectPtr(), 1 => MI_ParameterSet.NewDirectPtr(),
        2 => MI_QualifierSet.NewIndirectPtr(), 3 => MI_ParameterSet.NewIndirectPtr(),
        4 => MI_QualifierSet.NewFromDirectPtr(borrowed), _ => MI_ParameterSet.NewFromDirectPtr(borrowed)
    };
    [MethodImpl(MethodImplOptions.NoInlining)]
    static WeakReference[] Abandon(IntPtr borrowed)
    {
        var values = new WeakReference[192];
        for (int i=0; i<values.Length; i++)
        {
            var view = NewView(i%6, borrowed);
            Require((IntPtr)Allocation.GetValue(view) != IntPtr.Zero, "View owns a wrapper allocation");
            values[i] = new WeakReference(view, true);
        }
        return values;
    }
    static void Allocations(bool baseline)
    {
        IntPtr borrowed=Marshal.AllocHGlobal(64);
        try
        {
            Marshal.WriteInt64(borrowed, 0x123456789abcdef);
            for(int kind=0;kind<6;kind++)
            {
                var view=NewView(kind,borrowed);
                view.Dispose(); view.Dispose();
                Require((IntPtr)Allocation.GetValue(view)==IntPtr.Zero, "Explicit disposal releases its allocation once: "+kind);
                Require(Marshal.ReadInt64(borrowed)==0x123456789abcdef, "Explicit disposal preserves borrowed metadata: "+kind);
            }
            var values=Abandon(borrowed);
            GC.Collect(2,GCCollectionMode.Forced,true,true); GC.WaitForPendingFinalizers();
            // Long weak references let us inspect objects after their finalizers
            // and before another collection. No GC is requested in this loop.
            int finalized=0,released=0;
            foreach(var weak in values)
            {
                object value=weak.Target;
                if(value==null)continue;
                finalized++;
                if((IntPtr)Allocation.GetValue(value)==IntPtr.Zero)released++;
            }
            Console.WriteLine("Metadata views: allocated="+values.Length+" finalized="+finalized+" released="+released);
            if(baseline) Require(finalized==0 && released==0, "Installed baseline has no metadata-view allocation finalizers");
            else Require(finalized==values.Length && released==values.Length, "Every abandoned direct/indirect/borrowed view released its wrapper allocation");
            Require(Marshal.ReadInt64(borrowed)==0x123456789abcdef,"Automatic cleanup preserves borrowed native class metadata");
        }
        finally { Marshal.FreeHGlobal(borrowed); }
    }
    static void Qualifiers(System.Collections.Generic.IEnumerable<CimQualifier> values)
    {
        foreach(var qualifier in values)
        {
            Require(!string.IsNullOrEmpty(qualifier.Name),"Qualifier name");
            _=qualifier.Value; _=qualifier.CimType; _=qualifier.Flags;
        }
    }
    static void LiveMetadata()
    {
        using var session=CimSession.Create(null);
        using var cls=session.GetClass("root/cimv2","Win32_Process");
        using var stop=new CancellationTokenSource();
        var collector=Task.Run(()=> {while(!stop.IsCancellationRequested){GC.Collect(2,GCCollectionMode.Forced,true,true);Thread.Sleep(2);}});
        try
        {
            for(int iteration=0;iteration<8;iteration++)
            {
                Require(cls.CimClassQualifiers.Count>0,"Class qualifier count");
                Qualifiers(cls.CimClassQualifiers);
                foreach(var property in cls.CimClassProperties)
                {
                    Require(cls.CimClassProperties[property.Name]!=null,"Property name lookup");
                    _=property.Value;_=property.CimType;_=property.Flags;
                    Qualifiers(property.Qualifiers);
                }
                foreach(var method in cls.CimClassMethods)
                {
                    Require(cls.CimClassMethods[method.Name]!=null,"Method name lookup");
                    Require(method.ReturnType==CimType.UInt32,"Win32_Process method return type");
                    Qualifiers(method.Qualifiers);
                    foreach(var parameter in method.Parameters)
                    {
                        Require(method.Parameters[parameter.Name]!=null,"Parameter name lookup");
                        _=parameter.CimType;_=parameter.ReferenceClassName;
                        Qualifiers(parameter.Qualifiers);
                    }
                }
            }
            GC.KeepAlive(cls);
        }
        finally {stop.Cancel();collector.GetAwaiter().GetResult();}
        Require(cls.CimClassMethods["Create"].Parameters["CommandLine"].CimType==CimType.String,"Borrowed live class metadata remains valid after repeated GC");
    }
    static int Main(string[] args)
    {
        try
        {
            bool baseline=args.Contains("--baseline");
            Allocations(baseline);
            if(baseline){Console.WriteLine("REPRODUCED abandoned qualifier/parameter wrapper allocations without automatic reclamation");return 0;}
            LiveMetadata();
            Console.WriteLine("PASS "+checks+" metadata allocation/disposal/borrowed-memory and live qualifier/parameter GC checks");
            return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
}
