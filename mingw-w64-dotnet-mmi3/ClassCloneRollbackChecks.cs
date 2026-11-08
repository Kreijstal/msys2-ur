using System;
using System.Linq;
using System.Runtime.InteropServices;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Internal;
using Microsoft.Management.Infrastructure.Native;

static class ClassCloneRollbackChecks
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate void Reset(int index);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate IntPtr Source(uint index);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate int Count(uint kind,uint index);
    static int checks;
    static void Require(bool value,string message){checks++;if(!value)throw new Exception(message);}
    static void Case(Reset reset,Source source,Count count,int[] indices,int failure,bool baseline)
    {
        reset(failure);
        var inputs=indices.Select(index=>index<0?null:MI_Class.NewFromDirectPtr(source((uint)index))).ToArray();
        MI_Class[] outputs=null;
        bool failed=false;
        try
        {
            try {outputs=inputs.CloneMIArray();}
            catch(CimException error){Require(error.NativeErrorCode==NativeErrorCode.Failed,"Original native clone failure");failed=true;}
            Require(failed==(failure>=0&&indices.Contains(failure)),"Clone outcome");
            if(baseline)
            {
                Require(Enumerable.Range(0,16).Sum(i=>count(0,(uint)i))>0,"Installed baseline deletes caller-owned source handles");
                Require(Enumerable.Range(0,16).Sum(i=>count(2,(uint)i))==0,"Installed baseline fails to delete created output clones");
                Console.WriteLine("REPRODUCED source deletion and leaked output clones on native class-array failure");return;
            }
            for(uint i=0;i<16;i++)Require(count(0,i)==0,"Caller-owned source was not deleted: "+i);
            foreach(var input in inputs.Where(x=>x!=null))
            {
                Require(input.GetClassName(out var name)==MI_Result.MI_RESULT_OK&&name=="MSYS2_CloneSource","Original source remains usable after clone/rollback");
            }
            if(failed)
            {
                for(uint i=0;i<16;i++)Require(count(1,i)==count(2,i),"Only created output clones reclaimed, including after null holes: "+i);
            }
            else
            {
                Require(outputs.Length==inputs.Length,"Array length preserved");
                for(int i=0;i<inputs.Length;i++)Require((inputs[i]==null)==(outputs[i]==null),"Null slot preserved");
            }
        }
        finally
        {
            if(outputs!=null)foreach(var output in outputs)if(output!=null){output.Delete();output.Dispose();output.Dispose();}
            foreach(var input in inputs)input?.Dispose();
            if(!baseline)for(uint i=0;i<16;i++)Require(count(1,i)==count(2,i),"Output clones released exactly once: "+i);
        }
    }
    static int Main(string[] args)
    {
        IntPtr library=IntPtr.Zero;
        try
        {
            bool baseline=args.Contains("--baseline");
            library=NativeLibrary.Load(System.IO.Path.Combine(AppContext.BaseDirectory,"class-clone-driver.dll"));
            var reset=Marshal.GetDelegateForFunctionPointer<Reset>(NativeLibrary.GetExport(library,"reset_driver"));
            var source=Marshal.GetDelegateForFunctionPointer<Source>(NativeLibrary.GetExport(library,"source_class"));
            var count=Marshal.GetDelegateForFunctionPointer<Count>(NativeLibrary.GetExport(library,"driver_count"));
            if(baseline){Case(reset,source,count,new[]{0,1,2},1,true);Case(reset,source,count,new[]{0,-1,2,3},3,true);}
            else
            {
                reset(0);
                using(var input=MI_Class.NewFromDirectPtr(source(0)))
                {
                    Require(input.Clone(out var failedOutput)==MI_Result.MI_RESULT_FAILED&&failedOutput==null,"Failed native clone releases output wrapper and exposes no owned output");
                    Require(count(0,0)==0,"Failed single clone preserves source");
                }
                bool rejected=false;try{ClassHandleExtensionMethods.CloneMIArray(null);}catch(ArgumentNullException){rejected=true;}
                Require(rejected,"Null source array rejected");
                Case(reset,source,count,Array.Empty<int>(),-1,false);
                Case(reset,source,count,new[]{-1,-1},-1,false);
                Case(reset,source,count,new[]{0,-1,2},-1,false);
                foreach(var indices in new[]{new[]{0,1,2},new[]{0,-1,2,3}})
                    foreach(int failure in indices.Where(i=>i>=0))Case(reset,source,count,indices,failure,false);
            }
            reset(-1);
            Console.WriteLine("PASS "+checks+" native class clone/rollback/source-preservation/null-slot/cleanup checks"+(baseline?" (baseline reproduction)":""));return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
        finally {if(library!=IntPtr.Zero)NativeLibrary.Free(library);}
    }
}
