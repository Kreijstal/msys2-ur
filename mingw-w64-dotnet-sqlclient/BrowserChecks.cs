// Independent MC-SQLR UDP peer; no SQL Browser service or database engine.
using System;
using System.Buffers.Binary;
using System.Data.SqlClient;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Threading;

internal static class BrowserChecks
{
    static int checks, defects;
    static readonly Type Browser = typeof(SqlConnection).Assembly.GetType("System.Data.SqlClient.SNI.SSRP",true);
    static void Require(bool condition,string message){checks++;if(!condition)throw new Exception(message);}
    static byte[] Instance(string fields)
    {
        byte[] body=Encoding.ASCII.GetBytes(fields), result=new byte[body.Length+3];result[0]=5;
        BinaryPrimitives.WriteUInt16LittleEndian(result.AsSpan(1),checked((ushort)body.Length));body.CopyTo(result,3);return result;
    }
    static byte[] Dac(ushort port){byte[] b={5,6,0,1,0,0};BinaryPrimitives.WriteUInt16LittleEndian(b.AsSpan(4),port);return b;}
    static async Task Scenario(string name,bool dac,byte[] reply,int? expected,bool baseline)
    {
        using var peer=new UdpClient(AddressFamily.InterNetwork);
        peer.Client.ExclusiveAddressUse=true;peer.Client.Bind(new IPEndPoint(IPAddress.Loopback,1434));
        const string instance="source_instance";
        var responder=Task.Run(async()=>
        {
            var request=await peer.ReceiveAsync().WaitAsync(TimeSpan.FromSeconds(4));
            byte[] wanted=Encoding.ASCII.GetBytes((dac?"\x0f\x01":"\x04")+instance+"\0");
            Require(request.Buffer.AsSpan().SequenceEqual(wanted),name+" exact SQLR request bytes");
            await peer.SendAsync(reply,reply.Length,request.RemoteEndPoint);
        });
        Exception failure=null;int result=-1;
        try
        {
            result=(int)Browser.GetMethod(dac?"GetDacPortByInstanceName":"GetPortByInstanceName",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{"127.0.0.1",instance});
        }
        catch(TargetInvocationException error){failure=error.InnerException;}
        await responder;
        bool valid=expected.HasValue ? failure==null&&result==expected.Value : failure is SocketException;
        if(!valid&&baseline){defects++;Console.WriteLine("REPRODUCED "+name+" result="+result+" exception="+failure?.GetType().Name);}
        else Require(valid,name+" must "+(expected.HasValue?"return "+expected.Value:"reject with SocketException")+"; actual="+result+" "+failure);
    }
    static async Task PublicFailure(string name,bool dac,byte[] reply,bool baseline)
    {
        using var peer=new UdpClient(AddressFamily.InterNetwork);peer.Client.ExclusiveAddressUse=true;
        peer.Client.Bind(new IPEndPoint(IPAddress.Loopback,1434));
        var responder=Task.Run(async()=>{var request=await peer.ReceiveAsync().WaitAsync(TimeSpan.FromSeconds(4));Require(request.Buffer[0]==(dac?15:4),name+" request kind");await peer.SendAsync(reply,reply.Length,request.RemoteEndPoint);});
        var builder=new SqlConnectionStringBuilder{DataSource=(dac?"admin:":"tcp:")+"127.0.0.1\\source_instance",UserID="fixture",Password="fixture",Pooling=false,ConnectTimeout=3};
        using var connection=new SqlConnection(builder.ConnectionString);
        Exception failure=null;try{await connection.OpenAsync();}catch(Exception error){failure=error;}
        await responder;
        if(failure is not SqlException && baseline){defects++;Console.WriteLine("REPRODUCED public "+name+" "+failure?.GetType().Name);}
        else Require(failure is SqlException,name+" public OpenAsync returns SqlException; actual="+failure);
        Require(connection.State==System.Data.ConnectionState.Closed,name+" failed connection closed");
    }
    static async Task<byte[]> ReadPacket(Stream stream)
    {
        byte[] h=new byte[8];await stream.ReadExactlyAsync(h);int size=BinaryPrimitives.ReadUInt16BigEndian(h.AsSpan(2));
        Require(size>=8&&size<=32768,"valid TDS packet length");byte[] b=new byte[size];h.CopyTo(b,0);await stream.ReadExactlyAsync(b.AsMemory(8));return b;
    }
    static byte[] Packet(byte[] body)
    {
        byte[] b=new byte[body.Length+8];b[0]=4;b[1]=1;b[6]=1;BinaryPrimitives.WriteUInt16BigEndian(b.AsSpan(2),checked((ushort)b.Length));body.CopyTo(b,8);return b;
    }
    static void Done(BinaryWriter w,long count){w.Write((byte)0xfd);w.Write((ushort)(count==0?0:0x10));w.Write((ushort)0);w.Write(count);}
    static byte[] Login()
    {
        using var b=new MemoryStream();using var w=new BinaryWriter(b,Encoding.Unicode,true);const string name="BrowserFixture";
        w.Write((byte)0xad);w.Write((ushort)(10+2*name.Length));w.Write((byte)1);w.Write(new byte[]{0x74,0,0,4});w.Write((byte)name.Length);w.Write(Encoding.Unicode.GetBytes(name));w.Write(new byte[]{16,0,1,0});Done(w,0);return Packet(b.ToArray());
    }
    static byte[] Rows()
    {
        using var b=new MemoryStream();using var w=new BinaryWriter(b,Encoding.Unicode,true);
        w.Write((byte)0x81);w.Write((ushort)1);w.Write((uint)0);w.Write((ushort)0);w.Write((byte)0x38);w.Write((byte)1);w.Write(Encoding.Unicode.GetBytes("N"));w.Write((byte)0xd1);w.Write(42);Done(w,1);return Packet(b.ToArray());
    }
    static async Task PublicQuery(bool dac,bool mixed,bool asynchronous,bool baseline)
    {
        using var browser=new UdpClient(AddressFamily.InterNetwork);browser.Client.ExclusiveAddressUse=true;browser.Client.Bind(new IPEndPoint(IPAddress.Loopback,1434));
        var listener=new TcpListener(IPAddress.Loopback,0);listener.Start();int port=((IPEndPoint)listener.LocalEndpoint).Port;
        using var stop=new CancellationTokenSource(TimeSpan.FromSeconds(6));
        var peer=Task.Run(async()=>
        {
            var request=await browser.ReceiveAsync(stop.Token);Require(request.Buffer[0]==(dac?15:4),"public query discovery kind");
            byte[] reply=dac?Dac((ushort)port):Instance("ServerName;localhost;InstanceName;source_instance;IsClustered;No;Version;16.0.1;"+(mixed?"TcP":"tcp")+";"+port+";;");
            await browser.SendAsync(reply,reply.Length,request.RemoteEndPoint);
            using var socket=await listener.AcceptTcpClientAsync(stop.Token);using var stream=socket.GetStream();
            Require((await ReadPacket(stream))[0]==0x12,"discovered endpoint PRELOGIN");
            await stream.WriteAsync(Packet(new byte[]{0,0,11,0,6,1,0,17,0,1,0xff,16,0,1,0,0,0,2}));
            Require((await ReadPacket(stream))[0]==0x10,"discovered endpoint LOGIN7");await stream.WriteAsync(Login());
            var batch=await ReadPacket(stream);Require(batch[0]==1,"discovered endpoint SQL batch");
            int offset=8+BinaryPrimitives.ReadInt32LittleEndian(batch.AsSpan(8));Require(Encoding.Unicode.GetString(batch,offset,batch.Length-offset)=="SELECT 42","actual SQL batch");await stream.WriteAsync(Rows());
        });
        try
        {
            using var c=new SqlConnection(new SqlConnectionStringBuilder{DataSource=(dac?"admin:":"tcp:")+"127.0.0.1\\source_instance",UserID="fixture",Password="fixture",Pooling=false,Encrypt=false,ConnectTimeout=3}.ConnectionString);
            if(asynchronous)await c.OpenAsync();else c.Open();using var command=new SqlCommand("SELECT 42",c);
            Require(Convert.ToInt32(asynchronous?await command.ExecuteScalarAsync():command.ExecuteScalar())==42,"public discovered scalar");
            await peer;Console.WriteLine("PASS discovered query dac="+dac+" mixed="+mixed+" async="+asynchronous);
        }
        catch(SqlException) when(baseline&&mixed)
        {
            defects++;Console.WriteLine("REPRODUCED public mixed-case discovery query");stop.Cancel();try{await peer;}catch(OperationCanceledException){}
        }
        finally{listener.Stop();}
    }
    public static int Run(string[] args)
    {
        using var gate=new Mutex(false,@"Local\MSYS2SqlClientBrowserFixture");
        Require(gate.WaitOne(TimeSpan.FromSeconds(30)),"exclusive loopback SQLR fixture");
        try{return Execute(args).GetAwaiter().GetResult();}
        finally{gate.ReleaseMutex();}
    }
    static async Task<int> Execute(string[] args)
    {
        try
        {
            bool baseline=Array.IndexOf(args,"--baseline")>=0;
            string fields="ServerName;localhost;InstanceName;source_instance;IsClustered;No;Version;16.0.1;";
            await Scenario("normal",false,Instance(fields+"tcp;15433;;"),15433,baseline);
            await Scenario("mixed-case",false,Instance(fields+"TcP;15433;;"),15433,baseline);
            await Scenario("minimum",false,Instance(fields+"tcp;1;;"),1,baseline);
            await Scenario("maximum",false,Instance(fields+"tcp;65535;;"),65535,baseline);
            foreach(string port in new[]{"invalid","65536","-1","+1433"," 1433","1433 ","0",""})
                await Scenario("bad-port:"+port,false,Instance(fields+"tcp;"+port+";;"),null,baseline);
            await Scenario("no-tcp",false,Instance(fields+"np;\\\\localhost\\pipe\\sql\\query;;"),null,baseline);
            await Scenario("value-is-tcp",false,Instance("ServerName;tcp;InstanceName;1433;;"),null,baseline);
            await Scenario("duplicate-tcp",false,Instance(fields+"tcp;1433;tcp;1434;;"),null,baseline);
            await Scenario("oversized",false,Instance(fields+"np;"+new string('x',1024)+";tcp;1433;;"),null,baseline);
            await Scenario("bad-length",false,new byte[]{5,9,0,116,99,112},null,baseline);
            await Scenario("bad-opcode",false,new byte[]{4,1,0,0},null,baseline);
            await Scenario("short-header",false,new byte[]{5,0},null,baseline);
            await Scenario("dac-normal",true,Dac(15433),15433,baseline);
            await Scenario("dac-max",true,Dac(65535),65535,baseline);
            await Scenario("dac-truncated",true,new byte[]{5,6,0,1,42},null,baseline);
            await Scenario("dac-extra",true,new byte[]{5,6,0,1,42,42,99},null,baseline);
            await Scenario("dac-zero",true,Dac(0),null,baseline);
            await Scenario("dac-version",true,new byte[]{5,6,0,2,42,42},null,baseline);
            await PublicFailure("invalid-port",false,Instance(fields+"tcp;invalid;;"),baseline);
            await PublicFailure("dac-truncated",true,new byte[]{5,6,0,1,42},baseline);
            foreach(bool dac in new[]{false,true})foreach(bool asynchronous in new[]{false,true})await PublicQuery(dac,!dac,asynchronous,baseline);
            Require(!baseline||defects>0,"baseline must reproduce defects");
            Console.WriteLine((baseline?"REPRODUCED":"PASS")+" SQL Browser checks="+checks+" defects="+defects);return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
    static int Main(string[] args)=>Run(args);
}
