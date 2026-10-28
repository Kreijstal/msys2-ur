using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Text;
using Microsoft.ApplicationInsights;
using Microsoft.ApplicationInsights.Channel;
using Microsoft.ApplicationInsights.DataContracts;
using Microsoft.ApplicationInsights.Extensibility;
using Microsoft.CodeAnalysis;
using JsonSerializer=Microsoft.ApplicationInsights.Extensibility.Implementation.JsonSerializer;

internal sealed class RecordingChannel : ITelemetryChannel
{
    internal readonly List<ITelemetry> Items=new();
    internal int Flushes;
    public bool? DeveloperMode {get;set;}
    public string EndpointAddress {get;set;}="memory://source-build-fixture";
    public void Send(ITelemetry item)=>Items.Add(item);
    public void Flush()=>Flushes++;
    public void Dispose(){}
}
internal sealed class Initializer : ITelemetryInitializer
{
    public void Initialize(ITelemetry telemetry)=>telemetry.Context.GlobalProperties["fixture"]="source λ";
}
internal static class Check
{
    internal static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static void Main(string[] args)
    {
        var assembly=typeof(TelemetryClient).Assembly;
        Require(assembly.GetName().Version==new Version(2,23,0,29),"upstream assembly identity");
        Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()=="31bf3856ad364e35","public identity");
        Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion=="2.23.0+2faa7e8b157a431daa2e71785d68abd5fa817b53","source version");
        Require(Path.GetDirectoryName(assembly.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"consumer-local implementation");
        assembly.GetExportedTypes();
        using var channel=new RecordingChannel();
        using var configuration=new TelemetryConfiguration("00000000-0000-0000-0000-000000000001",channel);
        configuration.TelemetryInitializers.Add(new Initializer());
        configuration.TelemetryInitializers.Add(new OperationCorrelationTelemetryInitializer());
        var client=new TelemetryClient(configuration);
        client.TrackEvent("event λ",new Dictionary<string,string>{{"key","value λ"}},new Dictionary<string,double>{{"count",2}});
        client.TrackTrace("trace λ",SeverityLevel.Warning);
        client.TrackException(new InvalidOperationException("fixture λ"));
        client.TrackMetric("metric",12.5);
        using(var request=client.StartOperation<RequestTelemetry>("request"))
        {
            request.Telemetry.ResponseCode="200";request.Telemetry.Success=true;
            using(var dependency=client.StartOperation<DependencyTelemetry>("dependency"))
            {
                dependency.Telemetry.Type="fixture";dependency.Telemetry.Success=true;

            }
        }
        var recordedRequest=channel.Items.OfType<RequestTelemetry>().Single();
        var recordedDependency=channel.Items.OfType<DependencyTelemetry>().Single();
        Require(!string.IsNullOrEmpty(recordedRequest.Context.Operation.Id) && recordedDependency.Context.Operation.Id==recordedRequest.Context.Operation.Id,"trace correlation");
        Require(recordedDependency.Context.Operation.ParentId==recordedRequest.Id,"parent correlation");
        client.Flush();
        Require(channel.Items.Count==6&&channel.Flushes>0,"recorded telemetry count/flush");
        Require(channel.Items.All(t=>t.Context.GlobalProperties["fixture"]=="source λ"),"telemetry initialization");
        Require(channel.Items.OfType<EventTelemetry>().Single().Name=="event λ","event payload");
        Require(channel.Items.OfType<RequestTelemetry>().Single().Duration>=TimeSpan.Zero,"request duration");
        byte[] raw=JsonSerializer.Serialize(channel.Items,compress:false);
        using var compressed=new MemoryStream(JsonSerializer.Serialize(channel.Items,compress:true));
        using var gzip=new GZipStream(compressed,CompressionMode.Decompress);using var expanded=new MemoryStream();gzip.CopyTo(expanded);
        Require(raw.SequenceEqual(expanded.ToArray()),"gzip serialization");
        string payload=Encoding.UTF8.GetString(raw);
        Require(payload.Contains("fixture")&&payload.Contains("source λ")&&payload.Contains("EventData")&&payload.Contains("RequestData"),"telemetry envelope serialization");
        var clone=(EventTelemetry)channel.Items.OfType<EventTelemetry>().Single().DeepClone();
        clone.Properties["independent"]="clone";
        Require(!channel.Items.OfType<EventTelemetry>().Single().Properties.ContainsKey("independent"),"deep clone isolation");
        int count=channel.Items.Count;configuration.DisableTelemetry=true;client.TrackEvent("disabled");
        Require(channel.Items.Count==count,"disabled telemetry");
        var references=Directory.GetFiles(args[0],"*.dll").Select(p=>MetadataReference.CreateFromFile(p));
        CheckApi.Run(references,assembly.Location,args[1],typeof(Activity).Assembly.Location);
        Console.WriteLine("PASS ApplicationInsights identity/source/location; event/trace/exception/metric/request/dependency, correlation, initializer, clone, disable, flush and JSON/gzip; in-memory channel only");
    }
}
