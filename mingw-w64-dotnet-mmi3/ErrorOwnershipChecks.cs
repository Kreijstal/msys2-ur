// Public/internal CimException borrowing and independent error-data lifetime.
using System;
using System.Runtime.InteropServices;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Native;

public static class ErrorOwnershipChecks
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate IntPtr Reset(uint mode);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate uint Count(uint kind);
    public static string DriverPath { get; set; }
    static int checks,defects;
    static void Require(bool value,string message){checks++;if(!value)throw new Exception(message);}
    static void Case(Reset reset,Count count,uint mode,bool internalConstructor,bool baseline)
    {
        var handle=MI_Instance.NewFromDirectPtr(reset(mode));
        using var input=new CimInstance(handle);
        CimException result=null;Exception failure=null;
        try
        {
            try { result=internalConstructor ? new CimException(MI_Result.MI_RESULT_FAILED,"native detail",handle) : new CimException(input); }
            catch(Exception error){failure=error;}
            bool broken=baseline&&mode<4;
            if(broken)
            {
                Require(failure is ArgumentNullException&&result==null,"Baseline loses exception construction after deleting borrowed source: "+failure+" deletes="+count(0));
                Require(count(0)==1,"Baseline deletes caller/operation-owned error");
                defects++;Console.WriteLine("REPRODUCED borrowed error deletion mode="+mode+" internal="+internalConstructor);return;
            }
            Require(failure==null&&result!=null,"Exception construction succeeds");
            Require(count(0)==0,"Borrowed caller/provider error survives construction");
            Require(result.Message==(mode==4?"owned provider message":"MI_RESULT_FAILED"),"Provider message or original fallback");
            Require(result.MessageId=="owned-message-id","Independent error data metadata");
            Require(!ReferenceEquals(result.ErrorData,input),"Error data uses independent instance");
            Require(handle.GetClassName(out var name)==MI_Result.MI_RESULT_OK&&name=="Owned_Error","Borrowed source remains usable");
            if(internalConstructor)
            {
                input.Dispose();
                Require(result.MessageId=="owned-message-id","Owned error data survives source disposal");
            }
            result.Dispose();result.Dispose();result=null;
            Require(count(0)==(internalConstructor?1u:0u),"Disposing exception does not delete borrowed source");
            Require(count(1)==count(2),"All temporary and owned error clones deleted exactly once");
            if(!internalConstructor){input.Dispose();Require(count(0)==1,"Caller source deleted only by its owner");}
        }
        finally { result?.Dispose();(failure as IDisposable)?.Dispose(); }
    }
    public static int Run(string[] args)
    {
        IntPtr library=IntPtr.Zero;
        try
        {
            checks=defects=0;bool baseline=Array.IndexOf(args,"--baseline")>=0;
            library=NativeLibrary.Load(DriverPath??System.IO.Path.Combine(AppContext.BaseDirectory,"error-ownership-driver.dll"));
            var reset=Marshal.GetDelegateForFunctionPointer<Reset>(NativeLibrary.GetExport(library,"reset_driver"));
            var count=Marshal.GetDelegateForFunctionPointer<Count>(NativeLibrary.GetExport(library,"driver_count"));
            foreach(bool internalConstructor in new[]{false,true})for(uint mode=0;mode<5;mode++)Case(reset,count,mode,internalConstructor,baseline);
            using(var empty=MI_Instance.NewIndirectPtr())
            {
                if(baseline)
                {
                    bool rejected=false;try{using var error=new CimException(MI_Result.MI_RESULT_FAILED,null,empty);}catch(ArgumentNullException){rejected=true;}
                    Require(rejected,"Baseline mistakes empty native error wrapper for an error instance");defects++;
                }
                else
                {
                    using var error=new CimException(MI_Result.MI_RESULT_FAILED,null,empty);
                    Require(error.Message=="MI_RESULT_FAILED"&&error.ErrorData==null,"Empty native error details preserve native failure");
                }
            }
            Require(!baseline||defects==9,"Nine independent error-data regressions");
            Console.WriteLine((baseline?"REPRODUCED":"PASS")+" error-ownership checks="+checks+" defects="+defects);return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
        finally {if(library!=IntPtr.Zero)NativeLibrary.Free(library);}
    }
    static int Main(string[] args)=>Run(args);
}
