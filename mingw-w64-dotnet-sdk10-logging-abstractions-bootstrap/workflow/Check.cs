using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;

public static partial class Messages
{
    [LoggerMessage(EventId=42,Level=LogLevel.Information,Message="Hello {Name}: {Count}")]
    public static partial void Hello(ILogger logger,string name,int count);
}
internal sealed class Sink:ILogger
{
    public readonly List<(LogLevel Level,EventId Id,string Text,Dictionary<string,object?> State)> Entries=new();
    public bool Enabled=true;
    public int Scopes,Disposed;
    public bool IsEnabled(LogLevel level)=>Enabled;
    public IDisposable BeginScope<TState>(TState state) where TState:notnull { Scopes++;return new Scope(this); }
    public void Log<TState>(LogLevel level,EventId id,TState state,Exception? error,Func<TState,Exception?,string> formatter)
    {
        var fields=((IEnumerable<KeyValuePair<string,object?>>)(object)state!).ToDictionary(p=>p.Key,p=>p.Value);
        Entries.Add((level,id,formatter(state,error),fields));
    }
    sealed class Scope(Sink sink):IDisposable { public void Dispose()=>sink.Disposed++; }
}
internal interface IGreeting { string Text { get; } }
internal sealed class Greeting:IGreeting { public string Text=>"Hello 世界"; }
internal sealed class Provider(IGreeting greeting):IServiceProvider
{
    public object? GetService(Type type)=>type==typeof(IGreeting) ? greeting:null;
}
internal sealed class Constructed(IGreeting greeting,string suffix)
{
    public string Text=>greeting.Text+suffix;
}
internal static class Program
{
    static void Require(bool value,string message) { if(!value)throw new Exception(message); }
    public static int Main()
    {
        var services=new ServiceCollection();var greeting=new Greeting();
        services.AddSingleton<IGreeting>(greeting);services.TryAddEnumerable(new ServiceDescriptor(typeof(IDisposable),typeof(System.IO.MemoryStream),ServiceLifetime.Transient));
        Require(services.Any(d=>d.ServiceType==typeof(IGreeting) && d.Lifetime==ServiceLifetime.Singleton && ReferenceEquals(d.ImplementationInstance,greeting)),"Singleton descriptor");
        var keyed=ServiceDescriptor.KeyedSingleton<IGreeting>("世界",greeting);
        Require(keyed.IsKeyedService && Equals(keyed.ServiceKey,"世界") && ReferenceEquals(keyed.KeyedImplementationInstance,greeting),"Keyed descriptor");
        var instance=ActivatorUtilities.CreateInstance<Constructed>(new Provider(greeting),"!");Require(instance.Text=="Hello 世界!","Constructor injection and explicit argument");
        var logger=new Sink();Messages.Hello(logger,"世界",7);
        var entry=logger.Entries.Single();Require(entry.Level==LogLevel.Information && entry.Id.Id==42 && entry.Text=="Hello 世界: 7","Generated logging output");
        Require((string?)entry.State["Name"]=="世界" && (int)entry.State["Count"]! ==7 && (string?)entry.State["{OriginalFormat}"]=="Hello {Name}: {Count}","Structured generated values");
        logger.Enabled=false;Messages.Hello(logger,"ignored",99);Require(logger.Entries.Count==1,"Generated enabled guard");logger.Enabled=true;
        using(LoggerMessage.DefineScope<string>("Operation {Name}")(logger,"owned")) { Require(logger.Scopes==1,"Scope creation"); }
        Require(logger.Disposed==1,"Scope disposal");
        logger.LogWarning("Owned {Value}",123);Require(logger.Entries.Last().Level==LogLevel.Warning && (int)logger.Entries.Last().State["Value"]! ==123,"Logging extension values");
        Require(!NullLogger.Instance.IsEnabled(LogLevel.Critical),"Null logger");
        Console.WriteLine("PASS original DI descriptors/keyed services/constructor activation and generated Unicode/structured logging, enabled guard and scope lifetime");return 0;
    }
}
