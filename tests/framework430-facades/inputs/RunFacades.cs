using System;
using System.Collections.Generic;
using System.Diagnostics.Tracing;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.Loader;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

sealed class ProbeContext : AssemblyLoadContext
{
    internal ProbeContext() : base(isCollectible: true) { }
    protected override Assembly? Load(AssemblyName name) => Default.LoadFromAssemblyName(name);
}
static class RunFacades
{
    static void Require(bool condition, string message) { if (!condition) throw new Exception(message); }
    static object? Call(Type type, string name, Type[] signature, params object?[] args) => type.GetMethod(name, signature)!.Invoke(null, args);
    static async Task<object?> Complete(object result)
    {
        var task = (Task)result; await task.WaitAsync(TimeSpan.FromSeconds(10));
        return task.GetType().GetProperty("Result")?.GetValue(task);
    }
    static async Task Sockets(Assembly assembly)
    {
        Type extension = assembly.GetType("System.Net.Sockets.SocketTaskExtensions", true)!;
        Require(extension.Assembly == assembly, "Owned SocketTaskExtensions must execute candidate source");
        var array = typeof(ArraySegment<byte>); var list = typeof(IList<ArraySegment<byte>>);
        for (int round = 0; round != 4; round++)
        {
            using var listener = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
            listener.Bind(new IPEndPoint(IPAddress.Loopback, 0)); listener.Listen(2);
            using var client = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
            Socket? reusable = round == 3 ? new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp) : null;
            object accept = reusable == null ? Call(extension, "AcceptAsync", new[] { typeof(Socket) }, listener)! : Call(extension, "AcceptAsync", new[] { typeof(Socket), typeof(Socket) }, listener, reusable)!;
            var endpoint = (IPEndPoint)listener.LocalEndPoint!;
            object connect = round switch {
                0 => Call(extension, "ConnectAsync", new[] { typeof(Socket), typeof(EndPoint) }, client, endpoint)!,
                1 => Call(extension, "ConnectAsync", new[] { typeof(Socket), typeof(IPAddress), typeof(int) }, client, IPAddress.Loopback, endpoint.Port)!,
                2 => Call(extension, "ConnectAsync", new[] { typeof(Socket), typeof(IPAddress[]), typeof(int) }, client, new[] { IPAddress.Loopback }, endpoint.Port)!,
                _ => Call(extension, "ConnectAsync", new[] { typeof(Socket), typeof(string), typeof(int) }, client, "127.0.0.1", endpoint.Port)! };
            await Complete(connect); using var server = (Socket)(await Complete(accept))!;
            Require(reusable == null || ReferenceEquals(server, reusable), "Original accept-socket overload reuses the supplied socket");
            byte[] payload = Encoding.UTF8.GetBytes("source-" + round), received = new byte[payload.Length]; int sent = 0, read = 0;
            while (sent < payload.Length)
            {
                object buffer = round % 2 == 0 ? new ArraySegment<byte>(payload, sent, payload.Length - sent) : new List<ArraySegment<byte>> { new(payload, sent, payload.Length - sent) };
                int count = (int)(await Complete(Call(extension, "SendAsync", new[] { typeof(Socket), round % 2 == 0 ? array : list, typeof(SocketFlags) }, client, buffer, SocketFlags.None)!))!;
                Require(count > 0, "TCP send progress"); sent += count;
            }
            while (read < payload.Length)
            {
                object buffer = round % 2 == 0 ? new ArraySegment<byte>(received, read, received.Length - read) : new List<ArraySegment<byte>> { new(received, read, received.Length - read) };
                int count = (int)(await Complete(Call(extension, "ReceiveAsync", new[] { typeof(Socket), round % 2 == 0 ? array : list, typeof(SocketFlags) }, server, buffer, SocketFlags.None)!))!;
                Require(count > 0, "TCP receive progress"); read += count;
            }
            Require(payload.SequenceEqual(received), "Original source TCP connect/accept/send/receive payload");
        }
        for (int mode = 0; mode != 2; mode++)
        {
            using var receiver = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
            using var sender = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
            receiver.Bind(new IPEndPoint(IPAddress.Loopback, 0));
            if (mode == 1) receiver.SetSocketOption(SocketOptionLevel.IP, SocketOptionName.PacketInformation, true);
            byte[] payload = Encoding.UTF8.GetBytes("source-udp"), buffer = new byte[64];
            object pending = Call(extension, mode == 0 ? "ReceiveFromAsync" : "ReceiveMessageFromAsync", new[] { typeof(Socket), array, typeof(SocketFlags), typeof(EndPoint) }, receiver, new ArraySegment<byte>(buffer), SocketFlags.None, new IPEndPoint(IPAddress.Any, 0))!;
            int sent = (int)(await Complete(Call(extension, "SendToAsync", new[] { typeof(Socket), array, typeof(SocketFlags), typeof(EndPoint) }, sender, new ArraySegment<byte>(payload), SocketFlags.None, receiver.LocalEndPoint)!))!;
            object result = (await Complete(pending))!; Type resultType = result.GetType();
            Require(resultType.Assembly == assembly && (int)resultType.GetField("ReceivedBytes")!.GetValue(result)! == sent && buffer.Take(sent).SequenceEqual(payload), "Owned UDP result and payload");
            Require(resultType.GetField("RemoteEndPoint")!.GetValue(result) is IPEndPoint remote && remote.Address.Equals(IPAddress.Loopback), "UDP peer metadata");
            if (mode == 1) Require(((IPPacketInformation)resultType.GetField("PacketInformation")!.GetValue(result)!).Address.Equals(IPAddress.Loopback), "UDP packet destination metadata");
        }
        Console.WriteLine("PASS all 13 original source socket task overloads: four connects, two accepts, both send/receive forms and UDP results/packet metadata");
    }
    static void Counter(Assembly assembly)
    {
        Type counter = assembly.GetType("System.Diagnostics.Tracing.EventCounter", true)!;
        Require(counter.Assembly == assembly, "Owned EventCounter must execute candidate source");
        using var source = new EventSource("OriginalSourceCounter-" + Guid.NewGuid().ToString("N"));
        object value = Activator.CreateInstance(counter, "latency", source)!;
        counter.GetMethod("WriteMetric")!.Invoke(value, new object[] { 1f }); counter.GetMethod("WriteMetric")!.Invoke(value, new object[] { 3f });
        object payload = counter.GetMethod("GetEventCounterPayload", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(value, null)!;
        object? Read(string name) => payload.GetType().GetProperty(name)!.GetValue(payload);
        Require((int)Read("Count")! == 2 && (float)Read("Mean")! == 2f && (float)Read("Min")! == 1f && (float)Read("Max")! == 3f, "Original source EventCounter statistics");
        Console.WriteLine("PASS unchanged original EventCounter constructor, metric buffering and statistics on source NET8");
    }
    static async Task Main(string[] args)
    {
        var root = Path.GetFullPath(args[0]); using var profiles = JsonDocument.Parse(File.ReadAllText(args[1])); int forwarded = 0;
        foreach (var row in profiles.RootElement.EnumerateObject().Where(p => !p.Value.GetProperty("reference_source").GetBoolean()))
        {
            string name = row.Value.GetProperty("name").GetString()!, tfm = row.Value.GetProperty("framework").GetString()!;
            var context = new ProbeContext(); Assembly candidate = context.LoadFromAssemblyPath(Path.Combine(root, "ref", name, tfm, name + ".dll"));
            using var baseline = JsonDocument.Parse(File.ReadAllText(Path.Combine(args[2], row.Name + "-exports.json")));
            foreach (var export in baseline.RootElement[0].GetProperty("exported_types").EnumerateArray())
            {
                string typeName = export.GetProperty("full_name").GetString()!; Type type = candidate.GetType(typeName.Replace('/', '+'), true)!;
                Require(type.Assembly != candidate && type.Assembly.Location.Replace('\\', '/').Contains("/shared/Microsoft.NETCore.App/8.0.31/"), "Forwarded source runtime target: " + typeName); forwarded++;
            }
            if (name == "System.Diagnostics.Tracing") Counter(candidate);
            if (name == "System.Net.Sockets") await Sockets(candidate);
            context.Unload();
        }
        Require(forwarded == 94, "Every original exported-type record must resolve");
        Console.WriteLine("PASS all 94 original facade exports resolve to source NET8 implementations; historical Framework runtime remains unverified");
    }
}
