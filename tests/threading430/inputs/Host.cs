using System;
using System.IO;
using System.Reflection;
using System.Runtime.ExceptionServices;
using System.Runtime.Loader;

sealed class CandidateContext : AssemblyLoadContext
{
    readonly string candidate;
    internal CandidateContext(string path) : base(isCollectible:true) { candidate=path; }
    protected override Assembly? Load(AssemblyName name) => name.Name=="System.Threading" ? LoadFromAssemblyPath(candidate) : Default.LoadFromAssemblyName(name);
}
static class Host
{
    static void Main(string[] args)
    {
        var context=new CandidateContext(Path.GetFullPath(args[1]));
        var runner=context.LoadFromAssemblyPath(Path.GetFullPath(args[0]));
        try { object? result=runner.EntryPoint!.Invoke(null,Array.Empty<object>());if(result is not int checks||checks<900)throw new Exception("Expected completed candidate checks");Console.WriteLine("PASS actual source Threading4.0.12 candidate: "+checks+" countdown, barrier phase/cancellation, reader-writer ownership/contention, resource and exception checks"); }
        catch(TargetInvocationException error) when(error.InnerException!=null) { ExceptionDispatchInfo.Capture(error.InnerException).Throw(); }
        context.Unload();
    }
}
