using System;
using System.IO;
using System.Reflection;
using System.Runtime.Loader;
class Program
{
    sealed class SourceContext:AssemblyLoadContext
    {
        readonly string acl;
        internal SourceContext(string path):base("source-acl6",true){acl=path;}
        protected override Assembly Load(AssemblyName n)=>n.Name=="System.Security.AccessControl"?LoadFromAssemblyPath(acl):null;
    }
    static void Main(string[] args)
    {
        var acl=Path.GetFullPath(args[0]);AppContext.SetData("source-acl-directory",Path.GetDirectoryName(acl));
        var context=new SourceContext(acl);
        var assembly=context.LoadFromAssemblyPath(Path.GetFullPath(args[1]));
        try{assembly.GetType("Fixture").GetMethod("Run").Invoke(null,new object[]{args[2]});}
        catch(TargetInvocationException e){throw e.InnerException;}
        context.Unload();GC.Collect();GC.WaitForPendingFinalizers();
        Console.WriteLine("PASS source ACL6 implementation executed in isolated context; .NET 8 inbox remains available to normal consumers");
    }
}
