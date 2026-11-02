using System;
using System.IO;
using System.Reflection;
using System.Runtime.ExceptionServices;
using System.Runtime.Loader;

sealed class CandidateContext : AssemblyLoadContext
{
    readonly string candidate;
    internal CandidateContext(string path) : base(isCollectible:true) { candidate=path; }
    protected override Assembly? Load(AssemblyName name) => name.Name=="System.ObjectModel" ? LoadFromAssemblyPath(candidate) : Default.LoadFromAssemblyName(name);
}
static class Host
{
    static void Main(string[] args)
    {
        var context=new CandidateContext(Path.GetFullPath(args[1]));
        var runner=context.LoadFromAssemblyPath(Path.GetFullPath(args[0]));
        try { runner.EntryPoint!.Invoke(null,Array.Empty<object>()); }
        catch(TargetInvocationException error) when(error.InnerException!=null) { ExceptionDispatchInfo.Capture(error.InnerException).Throw(); }
        context.Unload();
    }
}
