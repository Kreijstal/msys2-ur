using Microsoft.DotNet.ApiSymbolExtensions.Logging;
using Microsoft.DotNet.GenAPI;
using Microsoft.DotNet.ApiSymbolExtensions;
using Microsoft.DotNet.ApiSymbolExtensions.Filtering;
using Microsoft.CodeAnalysis;
sealed class Logger:ILog
{
    public bool HasLoggedErrors{get;private set;}
    public void LogError(string message){HasLoggedErrors=true;System.Console.Error.WriteLine(message);}
    public void LogError(string code,string message)=>LogError(code+": "+message);
    public void LogWarning(string message)=>System.Console.Error.WriteLine("WARNING "+message);
    public void LogWarning(string code,string message)=>LogWarning(code+": "+message);
    public void LogMessage(string message)=>System.Console.WriteLine(message);
    public void LogMessage(MessageImportance importance,string message)=>LogMessage(message);
}
static class Program
{
    sealed class Interfaces:ISymbolFilter
    {
        readonly System.Collections.Generic.HashSet<string> names;
        internal Interfaces(string file){names=new(System.Text.Json.JsonSerializer.Deserialize<string[]>(System.IO.File.ReadAllText(file))!);}
        public bool Include(ISymbol symbol)=>!(symbol is IMethodSymbol method && method.AssociatedSymbol!=null) && (symbol is INamespaceSymbol || symbol.ContainingAssembly?.Name != "System" || (symbol is INamedTypeSymbol type?names.Contains(type.ToDisplayString()):symbol.ContainingType!=null && names.Contains(symbol.ContainingType.ToDisplayString())));
    }
    static int Main(string[] args)
    {
        var log=new Logger();
        if(args.Length==4)
        {
            var loader=new AssemblySymbolLoader(true,true);loader.AddReferenceSearchPaths(new[]{args[1]});var assembly=loader.LoadAssemblies(new[]{args[0]})[0]!;
            using var text=System.IO.File.CreateText(args[2]);using var builder=new CSharpFileBuilder(log,new CompositeSymbolFilter().Add(new AccessibilitySymbolFilter(true,true,true)).Add(new Interfaces(args[3])),new AccessibilitySymbolFilter(true,true,true),text,null,false,loader.MetadataReferences);builder.WriteAssembly(assembly);
        }
        else GenAPIApp.Run(log,new GenAPIApp.Context(new[]{args[0]},new[]{args[1]},args[2],null,null,null,null,false,true));return log.HasLoggedErrors?1:0;
    }
}
