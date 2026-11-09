using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text.Json;

static class InspectAbi
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate IntPtr SourceApplication();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate uint EnteredCount();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate UIntPtr ObservedDeclaration();
    static object Probe(Assembly assembly,string libraryPath)
    {
        IntPtr library=NativeLibrary.Load(libraryPath);object app=null,decl=null,output=null;
        try
        {
            var source=Marshal.GetDelegateForFunctionPointer<SourceApplication>(NativeLibrary.GetExport(library,"source_application"));
            var entered=Marshal.GetDelegateForFunctionPointer<EnteredCount>(NativeLibrary.GetExport(library,"entered_count"));
            var observed=Marshal.GetDelegateForFunctionPointer<ObservedDeclaration>(NativeLibrary.GetExport(library,"observed_declaration"));
            const BindingFlags flags=BindingFlags.NonPublic|BindingFlags.Static;
            var appType=assembly.GetType("Microsoft.Management.Infrastructure.Native.MI_Application",true);
            var declType=assembly.GetType("Microsoft.Management.Infrastructure.Native.MI_ClassDecl",true);
            app=appType.GetMethod("NewFromDirectPtr",flags).Invoke(null,new object[]{source()});
            decl=declType.GetMethod("NewDirectPtr",flags).Invoke(null,null);
            var nativeObject=assembly.GetType("Microsoft.Management.Infrastructure.Native.MI_NativeObject",true);
            IntPtr expected=(IntPtr)nativeObject.GetProperty("Ptr",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(decl);
            object[] parameters={decl,"OwnedNamespace","OwnedServer",null};string failure=null,detail=null;
            try{appType.GetMethod("NewClass",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(app,parameters);output=parameters[3];}
            catch(TargetInvocationException error){failure=error.InnerException.GetType().Name;detail=error.InnerException.ToString();}
            var deleteType=assembly.GetType("Microsoft.Management.Infrastructure.Native.MI_SubscriptionDeliveryOptions+MI_SubscriptionDeliveryOptionsFT+MI_SubscriptionDeliveryOptions_Delete",true);
            var delete=Marshal.GetDelegateForFunctionPointer(NativeLibrary.GetExport(library,"probe_delete"),deleteType);
            var pointer=Activator.CreateInstance(deleteType.GetMethod("Invoke").GetParameters()[0].ParameterType);
            object status=delete.DynamicInvoke(pointer);
            return new {captured_delete_status=status==null?(int?)null:Convert.ToInt32(status),exception_type=failure,exception_detail=detail,native_calls=entered(),expected_declaration=expected.ToString("x"),observed_declaration=observed().ToUInt64().ToString("x"),uses_real_provider=false};
        }
        finally{(output as IDisposable)?.Dispose();(decl as IDisposable)?.Dispose();(app as IDisposable)?.Dispose();NativeLibrary.Free(library);}
    }
    static object Parameter(ParameterInfo p)
    {
        Type type=p.ParameterType.IsByRef?p.ParameterType.GetElementType():p.ParameterType;
        return new {name=p.Name,type=p.ParameterType.FullName,by_ref=p.ParameterType.IsByRef,marshal_as=p.GetCustomAttribute<MarshalAsAttribute>()?.Value.ToString(),enum_size=type.IsEnum?(int?)Marshal.SizeOf(Enum.GetUnderlyingType(type)):null};
    }
    static int Main(string[] args)
    {
        var assembly=Assembly.LoadFrom(Path.GetFullPath(args[0]));
        var tables=assembly.GetTypes().Where(t=>t.Name.EndsWith("FT",StringComparison.Ordinal)&&t.Name.StartsWith("MI_",StringComparison.Ordinal)).OrderBy(t=>t.Name).Select(t=>new {
            name=t.Name,managed_type=t.FullName,
            fields=t.GetFields(BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).OrderBy(f=>f.MetadataToken).Select(f=>{
                var invoke=f.FieldType.GetMethod("Invoke");var convention=f.FieldType.GetCustomAttribute<UnmanagedFunctionPointerAttribute>();
                return new {name=f.Name,type=f.FieldType.FullName,offset=Marshal.OffsetOf(t,f.Name).ToInt64(),calling_convention=convention?.CallingConvention.ToString(),charset=convention?.CharSet.ToString(),return_type=invoke?.ReturnType.FullName,return_marshal_as=invoke?.ReturnParameter.GetCustomAttribute<MarshalAsAttribute>()?.Value.ToString(),parameters=invoke?.GetParameters().Select(Parameter).ToArray()};
            }).ToArray(),size=Marshal.SizeOf(t)
        }).ToArray();
        string prefix="Microsoft.Management.Infrastructure.Native.";
        string[] names={"MI_NativeObject+DirectPtr","MI_NativeObject+IndirectPtr","MI_String","MI_UserCredentials","MI_Interval","MI_Datetime","MI_SessionCreationCallbacks+MI_SessionCreationCallbacksNative","MI_ClassDecl+MI_ClassDeclMembers"};
        var structures=names.Select(name=>{
            var type=assembly.GetType(prefix+name,true);
            return new {name,size=Marshal.SizeOf(type),fields=type.GetFields(BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).Select(f=>new {name=f.Name,offset=Marshal.OffsetOf(type,f.Name).ToInt64()}).ToArray()};
        }).ToArray();
        var declaration=assembly.GetType(prefix+"MI_ClassDecl",true);
        string declarationError=null;
        try { _=Marshal.SizeOf(declaration); } catch(ArgumentException error){declarationError=error.GetType().Name;}
        File.WriteAllText(args[1],JsonSerializer.Serialize(new {assembly_identity=assembly.FullName,assembly_path=assembly.Location,platform=RuntimeInformation.ProcessArchitecture.ToString(),tables,structures,binding_probe=args.Length>2?Probe(assembly,Path.GetFullPath(args[2])):null,class_decl_wrapper_layout=declaration.StructLayoutAttribute.Value.ToString(),class_decl_wrapper_marshal_error=declarationError},new JsonSerializerOptions{WriteIndented=true}));
        Console.WriteLine("PASS reflected native MMI function-table metadata: "+tables.Length);return 0;
    }
}
