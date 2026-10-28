using System;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.ServiceModel;
using System.ServiceModel.Channels;
using System.Text;
using System.Threading.Tasks;
using System.Xml;
using System.Xml.Linq;
using System.Web.Services.Description;
using Message = System.ServiceModel.Channels.Message;

[ServiceContract(Namespace="urn:msys2")]
public interface IEcho
{
    [OperationContract(Action="urn:msys2/Echo", ReplyAction="*")]
    string Echo(string value);
}

internal static class Probe
{
    private static void Require(bool value,string message) { if(!value) throw new Exception(message); }
    private static async Task<string> Serve(TcpListener listener)
    {
        using var client=await listener.AcceptTcpClientAsync();
        using var stream=client.GetStream();
        return await ServeSoap(stream);
    }
    internal static async Task<string> ServeSoap(Stream stream)
    {
        using var reader=new StreamReader(stream,Encoding.UTF8,false,4096,true);
        var first=await reader.ReadLineAsync();
        Require(first!.StartsWith("POST /echo HTTP/1.1"),"Wrong SOAP HTTP request line");
        int length=0;
        bool action=false;
        while(true) {
            var line=await reader.ReadLineAsync();
            if(string.IsNullOrEmpty(line)) break;
            if(line.StartsWith("Content-Length:",StringComparison.OrdinalIgnoreCase)) length=int.Parse(line.Split(':')[1].Trim());
            if(line.StartsWith("SOAPAction:",StringComparison.OrdinalIgnoreCase)) action=line.Contains("urn:msys2/Echo");
        }
        Require(length>0 && action,"Missing SOAP length/action");
        // The probe requests ASCII text, so the HTTP byte length is also the
        // character count. Unicode is separately checked through WCF encoders.
        var body=new char[length];
        Require(await reader.ReadBlockAsync(body.AsMemory())==length,"Incomplete HTTP request body");
        var xml=XDocument.Parse(new string(body));
        XNamespace soap="http://schemas.xmlsoap.org/soap/envelope/";
        XNamespace service="urn:msys2";
        string value=xml.Root!.Element(soap+"Body")!.Element(service+"Echo")!.Element(service+"value")!.Value;
        var reply=new XDocument(new XElement(soap+"Envelope",new XAttribute(XNamespace.Xmlns+"s",soap),
            new XElement(soap+"Body",new XElement(service+"EchoResponse",new XElement(service+"EchoResult",value)))));
        byte[] payload=Encoding.UTF8.GetBytes(reply.ToString(SaveOptions.DisableFormatting));
        byte[] headers=Encoding.ASCII.GetBytes("HTTP/1.1 200 OK\r\nContent-Type: text/xml; charset=utf-8\r\nContent-Length: "+payload.Length+"\r\nConnection: close\r\n\r\n");
        await stream.WriteAsync(headers);await stream.WriteAsync(payload);await stream.FlushAsync();
        return value;
    }
    private static void Encoders()
    {
        foreach(MessageEncodingBindingElement binding in new MessageEncodingBindingElement[] {
            new TextMessageEncodingBindingElement(MessageVersion.Soap12WSAddressing10,Encoding.UTF8),
            new BinaryMessageEncodingBindingElement(),
            new MtomMessageEncodingBindingElement(MessageVersion.Soap12WSAddressing10,Encoding.UTF8) }) {
            var encoder=binding.CreateMessageEncoderFactory().Encoder;
            using var message=Message.CreateMessage(encoder.MessageVersion,"urn:msys2/Unicode","Unicode \u03bb & <xml>");
            using var bytes=new MemoryStream();encoder.WriteMessage(message,bytes);bytes.Position=0;
            using var decoded=encoder.ReadMessage(bytes,65536);
            Require(decoded.Headers.Action=="urn:msys2/Unicode" && decoded.GetBody<string>()=="Unicode \u03bb & <xml>","Message encoder round trip failed");
        }
        Console.WriteLine("PASS: SOAP text, binary and MTOM message encoders preserve Unicode/body/action");
    }
    private static void Wsdl()
    {
        const string wsdl="<definitions xmlns='http://schemas.xmlsoap.org/wsdl/' targetNamespace='urn:msys2' name='Echo'><message name='Input'/><portType name='EchoPort'/></definitions>";
        using var reader=XmlReader.Create(new StringReader(wsdl));
        var description=ServiceDescription.Read(reader);
        Require(description.Name=="Echo" && description.Messages.Count==1 && description.PortTypes.Count==1,"WSDL parse failed");
        using var output=new StringWriter();description.Write(output);
        using var again=XmlReader.Create(new StringReader(output.ToString()));
        Require(ServiceDescription.Read(again).TargetNamespace=="urn:msys2","WSDL serialization failed");
        Console.WriteLine("PASS: WSDL reader/writer round trip preserves descriptions");
    }
    private static async Task<int> Main(string[] args)
    {
        try {
            Console.WriteLine("Runtime: "+RuntimeInformation.FrameworkDescription);
            Console.WriteLine("WCF: "+typeof(ChannelFactory<>).Assembly.FullName);
            if(args.Length>0) CheckAssets.Run(args[0],args[1]);
            Encoders();Wsdl();
            await TransportProbe.Run();
            await SecurityProbe.Run();
            var listener=new TcpListener(IPAddress.Loopback,0);listener.Start();
            try {
                int port=((IPEndPoint)listener.LocalEndpoint).Port;
                var server=Serve(listener);
                var binding=new BasicHttpBinding(BasicHttpSecurityMode.None) { SendTimeout=TimeSpan.FromSeconds(10),OpenTimeout=TimeSpan.FromSeconds(10) };
                using var factory=new ChannelFactory<IEcho>(binding,new EndpointAddress("http://127.0.0.1:"+port+"/echo"));
                var channel=factory.CreateChannel();
                string result=channel.Echo("source-built SOAP & XML");
                Require(result=="source-built SOAP & XML" && await server==result,"SOAP request/response mismatch");
                ((IClientChannel)channel).Close();
                Console.WriteLine("PASS: real ChannelFactory/DispatchProxy/DataContractSerializer SOAP call over private loopback TCP server");
            } finally { listener.Stop(); }
            return 0;
        } catch(Exception error) { Console.Error.WriteLine(error);return 1; }
    }
}
