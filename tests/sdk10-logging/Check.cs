using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.IO;
using System.Linq;
using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

public sealed class Settings
{
    [Required, MinLength(3)] public string Name { get; set; } = "";
    [Range(1, 20)] public int Count { get; set; }
}
[OptionsValidator]
public partial class SettingsValidator : IValidateOptions<Settings> { }
public sealed class Owned : IDisposable
{
    public bool Disposed;
    public void Dispose() => Disposed = true;
}
internal static class Program
{
    static void Require(bool ok, string message) { if (!ok) throw new Exception(message); }
    static int Main()
    {
        var validator = new SettingsValidator();
        Require(validator.Validate(null, new Settings { Name="Grüße 世界",Count=4 }).Succeeded,"generated validation success");
        var invalid=validator.Validate(null,new Settings {Name="",Count=40});
        Require(invalid.Failed && invalid.Failures.Count()==2,"generated validation required/range failures");
        var configuration=new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string,string?> {
            ["App:Name"]="Grüße 世界",["App:Count"]="4",
            ["Logging:LogLevel:Default"]="Warning",
            ["Logging:Console:FormatterName"]="json",
            ["Logging:Console:FormatterOptions:IncludeScopes"]="true"
        }).Build();
        var services=new ServiceCollection();
        services.AddScoped<Owned>();services.AddKeyedSingleton<string>("unicode","世界");
        services.AddSingleton<IValidateOptions<Settings>>(validator);
        services.AddOptions<Settings>().Bind(configuration.GetSection("App"));
        services.AddLogging(builder=>builder.AddConfiguration(configuration.GetSection("Logging")).AddConsole());
        var saved=Console.Out;var captured=new StringWriter();Console.SetOut(captured);
        Owned owned;
        try
        {
            using(var provider=services.BuildServiceProvider(new ServiceProviderOptions {ValidateScopes=true,ValidateOnBuild=true}))
            {
                Require(provider.GetRequiredKeyedService<string>("unicode")=="世界","keyed DI");
                using(var scope=provider.CreateScope()) {owned=scope.ServiceProvider.GetRequiredService<Owned>();Require(ReferenceEquals(owned,scope.ServiceProvider.GetRequiredService<Owned>()),"scoped identity");}
                Require(owned.Disposed,"scoped disposal");
                var monitor=provider.GetRequiredService<IOptionsMonitor<Settings>>();
                Require(monitor.CurrentValue.Name=="Grüße 世界" && monitor.CurrentValue.Count==4,"configuration options binding");
                configuration["App:Count"]="6";configuration.Reload();
                Require(monitor.CurrentValue.Count==6,"options reload");
                var log=provider.GetRequiredService<ILoggerFactory>().CreateLogger("Owned.Consumer");
                Require(!log.IsEnabled(LogLevel.Information) && log.IsEnabled(LogLevel.Warning),"logging configuration filter");
                using(log.BeginScope("scope 世界")) {log.LogInformation("filtered");log.LogWarning(new EventId(42),"message {Name}","Grüße 世界");}
                configuration["App:Count"]="40";
                try { configuration.Reload(); } catch(AggregateException) { }
                bool rejected=false;try {_=monitor.CurrentValue;}catch(OptionsValidationException){rejected=true;}
                Require(rejected,"generated validator participates in options reload");
            }
        }
        finally {Console.SetOut(saved);}
        var lines=captured.ToString().Split(new[]{'\r','\n'},StringSplitOptions.RemoveEmptyEntries);
        Require(lines.Length==1,"queue flush and filtered output");
        using var json=JsonDocument.Parse(lines[0]);var root=json.RootElement;
        Require(root.GetProperty("EventId").GetInt32()==42 && root.GetProperty("Message").GetString()=="message Grüße 世界","JSON console event and Unicode");
        Require(root.GetProperty("Scopes").EnumerateArray().Any(s=>s.GetString()=="scope 世界"),"JSON console scopes");
        Require(AppDomain.CurrentDomain.GetAssemblies().Single(a=>a.GetName().Name=="Microsoft.Extensions.Logging.Console").Location.StartsWith(AppContext.BaseDirectory,StringComparison.OrdinalIgnoreCase),"consumer loads tested Console output");
        Console.WriteLine("PASS original NS2 Options generator: success/failure validation; NET10 DI scopes/disposal/keyed services; options binding/reload/rejection; configured logging/filtering; queued JSON Unicode/event/scopes and native Console construction");
        return 0;
    }
}
