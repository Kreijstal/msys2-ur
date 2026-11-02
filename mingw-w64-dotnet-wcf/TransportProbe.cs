using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.ServiceModel;
using System.ServiceModel.Channels;
using System.Text;
using System.Threading.Tasks;
using System.Xml.Linq;
using Message=System.ServiceModel.Channels.Message;

[ServiceContract(CallbackContract=typeof(IEchoCallback),Namespace="urn:msys2")]
public interface IDuplexEcho
{
    [OperationContract(IsOneWay=true,Action="urn:msys2/Publish")]
    void Publish(string value);
}
public interface IEchoCallback
{
    [OperationContract(IsOneWay=true,Action="urn:msys2/Callback")]
    void OnEcho(string value);
}
internal sealed class EchoCallback : IEchoCallback
{
    internal readonly TaskCompletionSource<string> Result=new(TaskCreationOptions.RunContinuationsAsynchronously);
    public void OnEcho(string value)=>Result.TrySetResult(value);
}

// Small independent peer for the framing protocol documented in the pinned
// upstream FramingFormat.cs. It tests actual client sockets/session encoding,
// request dispatch and callback dispatch without installing a service host.
internal static class TransportProbe
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static async Task<int> Byte(Stream stream)
    {
        byte[] bytes=new byte[1];await stream.ReadExactlyAsync(bytes);return bytes[0];
    }
    static async Task<int> Size(Stream stream)
    {
        int value=0;
        for(int shift=0;shift<35;shift+=7)
        {int b=await Byte(stream);value|=(b&127)<<shift;if((b&128)==0){Require(value>=0 && value<=1024*1024,"frame size");return value;}}
        throw new Exception("invalid frame size");
    }
    static async Task Frame(Stream stream,byte kind,ArraySegment<byte> bytes)
    {
        using var prefix=new MemoryStream();prefix.WriteByte(kind);
        int value=bytes.Count;
        do {byte b=(byte)(value&127);value>>=7;prefix.WriteByte((byte)(b|(value>0?128:0)));}while(value>0);
        await stream.WriteAsync(prefix.ToArray());await stream.WriteAsync(bytes.AsMemory());await stream.FlushAsync();
    }
    static async Task Peer(TcpListener listener,bool duplex)
    {
        using var client=await listener.AcceptTcpClientAsync();using var stream=client.GetStream();
        foreach(int expected in new[]{0,1,0,1,2,2})Require(await Byte(stream)==expected,"NetTcp version/mode/via record");
        byte[] via=new byte[await Size(stream)];await stream.ReadExactlyAsync(via);
        Require(Encoding.UTF8.GetString(via).StartsWith("net.tcp://127.0.0.1:"),"NetTcp via URI");
        Require(await Byte(stream)==3 && await Byte(stream)==8 && await Byte(stream)==12,"binary session/preamble end");
        await stream.WriteAsync(new byte[]{11});await stream.FlushAsync();
        Require(await Byte(stream)==6,"sized envelope");
        var buffers=BufferManager.CreateBufferManager(1024*1024,1024*1024);
        int length=await Size(stream);byte[] payload=buffers.TakeBuffer(length);
        await stream.ReadExactlyAsync(payload.AsMemory(0,length));
        var encoder=new BinaryMessageEncodingBindingElement().CreateMessageEncoderFactory().CreateSessionEncoder();
        using var request=encoder.ReadMessage(new ArraySegment<byte>(payload,0,length),buffers,encoder.ContentType);
        Require(request.Headers.Action==(duplex?"urn:msys2/Publish":"urn:msys2/Echo"),"NetTcp action");
        using var body=request.GetReaderAtBodyContents();var xml=(XElement)XElement.ReadFrom(body);XNamespace ns="urn:msys2";
        string value=xml.Element(ns+"value")!.Value;
        Require(value=="NetTcp λ & XML","NetTcp Unicode request");
        var response=new XElement(ns+(duplex?"OnEcho":"EchoResponse"),new XElement(ns+(duplex?"value":"EchoResult"),value));
        using var responseReader=response.CreateReader();
        using var reply=Message.CreateMessage(MessageVersion.Soap12WSAddressing10,duplex?"urn:msys2/Callback":"urn:msys2/EchoResponse",responseReader);
        reply.Headers.To=new Uri("http://www.w3.org/2005/08/addressing/anonymous");
        if(!duplex)reply.Headers.RelatesTo=request.Headers.MessageId;
        var bytes=encoder.WriteMessage(reply,1024*1024,buffers);
        await Frame(stream,6,bytes);buffers.ReturnBuffer(bytes.Array!);
        Require(await Byte(stream)==7,"NetTcp session close");
        await stream.WriteAsync(new byte[]{7});await stream.FlushAsync();
    }
    internal static async Task Run()
    {
        foreach(bool duplex in new[]{false,true})
        {
            var listener=new TcpListener(IPAddress.Loopback,0);listener.Start();
            try
            {
                int port=((IPEndPoint)listener.LocalEndpoint).Port;
                var server=Peer(listener,duplex);
                var binding=new NetTcpBinding(SecurityMode.None){OpenTimeout=TimeSpan.FromSeconds(10),SendTimeout=TimeSpan.FromSeconds(10),CloseTimeout=TimeSpan.FromSeconds(10)};
                var address=new EndpointAddress("net.tcp://127.0.0.1:"+port+"/echo");
                if(duplex)
                {
                    var callback=new EchoCallback();
                    var factory=new DuplexChannelFactory<IDuplexEcho>(new InstanceContext(callback),binding,address);
                    try {
                        var channel=factory.CreateChannel();channel.Publish("NetTcp λ & XML");
                        Require(await callback.Result.Task.WaitAsync(TimeSpan.FromSeconds(10))=="NetTcp λ & XML","duplex callback");
                        ((IClientChannel)channel).Close();factory.Close();
                    } catch {factory.Abort();if(server.IsFaulted)Console.Error.WriteLine(server.Exception);throw;}
                }
                else
                {
                    var factory=new ChannelFactory<IEcho>(binding,address);
                    try {
                        var channel=factory.CreateChannel();
                        Require(channel.Echo("NetTcp λ & XML")=="NetTcp λ & XML","NetTcp reply");
                        ((IClientChannel)channel).Close();factory.Close();
                    } catch {factory.Abort();if(server.IsFaulted)Console.Error.WriteLine(server.Exception);throw;}
                }
                await server.WaitAsync(TimeSpan.FromSeconds(10));
                Console.WriteLine(duplex?"PASS: DuplexChannelFactory NetTcp Unicode callback dispatch and session close":"PASS: NetTcpBinding framed binary session, Unicode SOAP request/reply and session close");
            }
            finally {listener.Stop();}
        }
    }
}
