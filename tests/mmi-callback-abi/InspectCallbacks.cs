using System;
using System.IO;
using System.Linq;
using System.Linq.Expressions;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;

static class InspectCallbacks
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate uint Size();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate uint Offset(uint slot);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate uint Populated(IntPtr pointer);
    const BindingFlags InstanceFlags=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
    const BindingFlags StaticFlags=BindingFlags.Static|BindingFlags.Public|BindingFlags.NonPublic;
    const string Prefix="Microsoft.Management.Infrastructure.Native.";
    static object Parameter(ParameterInfo p)
    {
        Type t=p.ParameterType.IsByRef?p.ParameterType.GetElementType():p.ParameterType;
        return new{name=p.Name,type=p.ParameterType.FullName,marshal_as=p.GetCustomAttribute<MarshalAsAttribute>()?.Value.ToString(),enum_size=t.IsEnum?(int?)Marshal.SizeOf(Enum.GetUnderlyingType(t)):null};
    }
    static object Signature(Type type)
    {
        var invoke=type.GetMethod("Invoke");var convention=type.GetCustomAttribute<UnmanagedFunctionPointerAttribute>();
        return new{name=type.FullName,return_type=invoke.ReturnType.FullName,calling_convention=convention.CallingConvention.ToString(),parameters=invoke.GetParameters().Select(Parameter).ToArray()};
    }
    static int Main(string[] args)
    {
        var assembly=Assembly.LoadFrom(Path.GetFullPath(args[0]));
        var bridgeType=assembly.GetType(Prefix+"MI_OperationCallbackBridge",true);
        var callbacksType=assembly.GetType(Prefix+"MI_OperationCallbacks",true);
        var operationType=assembly.GetType(Prefix+"MI_Operation",true);
        var signatures=bridgeType.GetNestedTypes(BindingFlags.Public|BindingFlags.NonPublic).Where(t=>typeof(Delegate).IsAssignableFrom(t)).Select(Signature).ToArray();
        var other=new[]{Prefix+"MI_Session+MI_SessionFT+MI_Session_Close_CompletionCallback",Prefix+"MI_Deserializer+MI_Deserializer_ClassObjectNeededNative",Prefix+"NativeMethods+MI_MainFunction",Prefix+"MI_SessionCreationCallbacks+MI_SessionCreationCallbacksNative+MI_SessionCallbacks_WriteErrorNative",Prefix+"MI_SessionCreationCallbacks+MI_SessionCreationCallbacksNative+MI_SessionCallbacks_WriteMessageNative"}.Select(n=>Signature(assembly.GetType(n,true))).ToArray();
        IntPtr library=NativeLibrary.Load(Path.GetFullPath(args[2]));object operation=null,bridge=null;
        uint size;uint[] offsets;int countBefore=(int)bridgeType.GetField("ActiveCount",StaticFlags).GetValue(null);uint populated;bool contextIsNull;
        string[] names={"promptUser","writeError","writeMessage","writeProgress","instanceResult","indicationResult","classResult","streamedParameterResult"};
        try
        {
            var callbacks=Activator.CreateInstance(callbacksType,true);
            foreach(string name in names)
            {
                var field=callbacksType.GetField(name,InstanceFlags);var invoke=field.FieldType.GetMethod("Invoke");
                if(invoke.ReturnType!=typeof(void))throw new Exception("Unexpected managed callback return");
                var parameters=invoke.GetParameters().Select(p=>Expression.Parameter(p.ParameterType,p.Name)).ToArray();
                field.SetValue(callbacks,Expression.Lambda(field.FieldType,Expression.Empty(),parameters).Compile());
            }
            operation=operationType.GetMethod("NewDirectPtr",StaticFlags).Invoke(null,null);
            IntPtr pointer=(IntPtr)operationType.GetMethod("SetCallbacks",InstanceFlags).Invoke(operation,new[]{callbacks});
            bridge=operationType.GetField("callbacks",InstanceFlags).GetValue(operation);
            size=Marshal.GetDelegateForFunctionPointer<Size>(NativeLibrary.GetExport(library,"callbacks_size"))();
            var offset=Marshal.GetDelegateForFunctionPointer<Offset>(NativeLibrary.GetExport(library,"callback_offset"));offsets=Enumerable.Range(0,9).Select(i=>offset((uint)i)).ToArray();
            populated=Marshal.GetDelegateForFunctionPointer<Populated>(NativeLibrary.GetExport(library,"populated_callbacks"))(pointer);
            contextIsNull=Marshal.ReadIntPtr(pointer)==IntPtr.Zero;
            if(size!=9*IntPtr.Size||populated!=8||!contextIsNull||offsets.Where((value,index)=>value!=index*IntPtr.Size).Any())throw new Exception("Callback storage ABI mismatch");
        }
        finally{(bridge as IDisposable)?.Dispose();(operation as IDisposable)?.Dispose();NativeLibrary.Free(library);}
        int countAfter=(int)bridgeType.GetField("ActiveCount",StaticFlags).GetValue(null);if(countAfter!=countBefore)throw new Exception("Callback roots leaked");
        var exports=new System.Collections.Generic.List<object>();
        foreach(var spec in new[]{("mi.dll",new[]{"MI_Application_InitializeV1","mi_clientFT_V1"}),("mimofcodec.dll",new[]{"MI_Application_NewSerializer_Mof","MI_Application_NewDeserializer_Mof"})})
        {
            IntPtr module=NativeLibrary.Load(spec.Item1);
            try
            {
                foreach(string name in spec.Item2)if(!NativeLibrary.TryGetExport(module,name,out var pointer)||pointer==IntPtr.Zero)throw new Exception("Required native export absent: "+name);
                var file=Process.GetCurrentProcess().Modules.Cast<ProcessModule>().Single(m=>m.ModuleName.Equals(spec.Item1,StringComparison.OrdinalIgnoreCase)).FileName;
                if(!Path.GetFullPath(file).StartsWith(Path.GetFullPath(Environment.SystemDirectory)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new Exception("Windows system module required");
                exports.Add(new{module=spec.Item1,path=file,version=FileVersionInfo.GetVersionInfo(file).FileVersion,sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(file))),symbols=spec.Item2});
            }
            finally{NativeLibrary.Free(module);}
        }
        var methods=assembly.GetType(Prefix+"NativeMethods",true).GetMethods(StaticFlags).Where(m=>m.GetCustomAttribute<DllImportAttribute>()!=null).Select(m=>new{name=m.Name,library=m.GetCustomAttribute<DllImportAttribute>().Value,calling_convention=m.GetCustomAttribute<DllImportAttribute>().CallingConvention.ToString(),return_type=m.ReturnType.FullName,return_marshal_as=m.ReturnParameter.GetCustomAttribute<MarshalAsAttribute>()?.Value.ToString(),parameters=m.GetParameters().Select(Parameter).ToArray()}).ToArray();
        File.WriteAllText(args[1],JsonSerializer.Serialize(new{assembly_identity=assembly.FullName,assembly_path=assembly.Location,bridge_signatures=signatures,other_signatures=other,storage_size=size,storage_offsets=offsets,populated_callbacks=populated,context_is_null=contextIsNull,root_count_before=countBefore,root_count_after=countAfter,exports,pinvoke_methods=methods,provider_connection_attempted=false},new JsonSerializerOptions{WriteIndented=true}));
        Console.WriteLine("PASS native callback storage, eight populated slots, root cleanup and four system exports");return 0;
    }
}
