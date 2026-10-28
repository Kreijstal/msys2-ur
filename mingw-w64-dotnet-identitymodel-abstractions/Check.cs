using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using Microsoft.IdentityModel.Abstractions;

[AttributeUsage(AttributeTargets.Method)] sealed class OwnedFactAttribute : Attribute {}
sealed class OwnedTelemetry : TelemetryEventDetails {}
static class Assert
{
    public static void Equal<T>(T expected,T actual) {if(!EqualityComparer<T>.Default.Equals(expected,actual))throw new Exception("Expected "+expected+"; actual "+actual);}
    public static void True(bool value) {if(!value)throw new Exception("Expected true");}
    public static void False(bool value) {True(!value);}
    public static void Throws<T>(string name,Action action) where T:ArgumentException
    {
        try {action();}catch(T error) {Equal(name,error.ParamName);return;}
        throw new Exception("Expected "+typeof(T).Name+" parameter "+name);
    }
}
class Program
{
    sealed class RecordingTelemetry : ITelemetryClient
    {
        public string ClientId {get;set;}
        public int Calls;
        public void Initialize() {Calls++;}
        public bool IsEnabled() {Calls++;return true;}
        public bool IsEnabled(string name) {Assert.Equal("owned",name);Calls++;return true;}
        public void TrackEvent(TelemetryEventDetails details) {Assert.Equal("owned",details.Name);Calls++;}
        public void TrackEvent(string name,IDictionary<string,string> strings=null,IDictionary<string,long> longs=null,
            IDictionary<string,bool> bools=null,IDictionary<string,DateTime> dates=null,
            IDictionary<string,double> doubles=null,IDictionary<string,Guid> guids=null)
        {Assert.Equal("owned",name);Assert.Equal("λ",strings["s"]);Assert.Equal(long.MaxValue,longs["n"]);Assert.True(bools["b"]);Assert.Equal(2024,dates["d"].Year);Assert.Equal(1.5,doubles["f"]);Assert.Equal(Guid.Empty,guids["g"]);Calls++;}
    }
    static void Main(string[] args)
    {
        var asm=typeof(TelemetryEventDetails).Assembly;
        Assert.Equal(Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"Microsoft.IdentityModel.Abstractions.dll")),Path.GetFullPath(asm.Location));
        Assert.Equal(args[0],Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(asm.Location))).ToLowerInvariant());
        Assert.Equal("6.35.0.0",asm.GetName().Version.ToString());
        Assert.Equal("6.35.0.41201",asm.GetCustomAttribute<AssemblyFileVersionAttribute>().Version);
        int cases=0;
        foreach(var type in Assembly.GetExecutingAssembly().GetTypes())
            foreach(var method in type.GetMethods().Where(m=>m.GetCustomAttribute<OwnedFactAttribute>()!=null))
            {method.Invoke(Activator.CreateInstance(type),null);cases++;Console.WriteLine("PASS original upstream assertion case "+method.Name);}
        Assert.Equal(6,cases);
        var details=new OwnedTelemetry {Name="owned λ"};var view=details.Properties;
        details.SetProperty("null",(string)null);details.SetProperty("",long.MaxValue);details.SetProperty("λ","😀");
        Assert.True(view.ContainsKey("null") && view["null"]==null);Assert.Equal(long.MaxValue,(long)view[""]);Assert.Equal("😀",(string)view["λ"]);
        details.Name="owned";
        ITelemetryClient recording=new RecordingTelemetry();recording.ClientId="owned-client";recording.Initialize();Assert.True(recording.IsEnabled());Assert.True(recording.IsEnabled("owned"));recording.TrackEvent(details);
        recording.TrackEvent("owned",new Dictionary<string,string>{{"s","λ"}},new Dictionary<string,long>{{"n",long.MaxValue}},
            new Dictionary<string,bool>{{"b",true}},new Dictionary<string,DateTime>{{"d",new DateTime(2024,1,1)}},new Dictionary<string,double>{{"f",1.5}},new Dictionary<string,Guid>{{"g",Guid.Empty}});
        Assert.Equal(5,((RecordingTelemetry)recording).Calls);
        var logger=NullIdentityModelLogger.Instance;Assert.True(ReferenceEquals(logger,NullIdentityModelLogger.Instance));
        foreach(EventLogLevel level in Enum.GetValues(typeof(EventLogLevel)))
        {Assert.False(logger.IsEnabled(level));logger.Log(new LogEntry {EventLogLevel=level,Message="owned λ",CorrelationId="😀"});}
        logger.Log(null);Assert.True(Enum.GetValues(typeof(EventLogLevel)).Cast<EventLogLevel>().Select(x=>(int)x).SequenceEqual(Enumerable.Range(0,6)));
        var entry=new LogEntry {Message="λ",CorrelationId="😀",EventLogLevel=EventLogLevel.Warning};Assert.Equal("λ",entry.Message);Assert.Equal("😀",entry.CorrelationId);
        var telemetry=NullTelemetryClient.Instance;Assert.True(ReferenceEquals(telemetry,NullTelemetryClient.Instance));
        telemetry.Initialize();Assert.False(telemetry.IsEnabled());Assert.False(telemetry.IsEnabled(null));telemetry.TrackEvent((TelemetryEventDetails)null);telemetry.TrackEvent((string)null);
        string old=telemetry.ClientId;try {telemetry.ClientId="owned λ";Assert.Equal("owned λ",telemetry.ClientId);}finally {telemetry.ClientId=old;}
        Assert.Equal("Succeeded",ObservabilityConstants.Succeeded);Assert.Equal("Duration",ObservabilityConstants.Duration);Assert.Equal("ActivityId",ObservabilityConstants.ActivityId);Assert.Equal("ClientId",ObservabilityConstants.ClientId);
        Console.WriteLine("PASS source Abstractions: six original telemetry cases, all interface overloads, live/null/Unicode data, original logger/telemetry singletons and constants; exact runtime bytes/location");
    }
}
