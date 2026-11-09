// Independent local SQLLocal IPC fixture; not a SQL Server database engine.
using System;
using System.IO;
using System.IO.Pipes;
using System.Net;
using System.Net.Sockets;
using System.Net.Security;
using System.Data.SqlClient;
using System.Buffers.Binary;
using System.Text;
using System.Reflection;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;

internal static class LpcChecks
{
    static int checks,defects;
    static void Require(bool value,string message){Interlocked.Increment(ref checks);if(!value)throw new Exception(message);}
    static readonly Type DataSource=typeof(SqlConnection).Assembly.GetType("System.Data.SqlClient.SNI.DataSource",true);
    static object Parse(string server)=>DataSource.GetMethod("ParseServerName").Invoke(null,new object[]{server});
    static object Property(object source,string name)=>DataSource.GetProperty(name,BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).GetValue(source);
    static string Protocol(object source)=>DataSource.GetField("ConnectionProtocol",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(source).ToString();
    static void Parser(string server,string instance,bool valid,bool baseline)
    {
        object parsed=Parse(server);
        bool correct=valid ? parsed!=null&&Protocol(parsed)=="LPC" : parsed==null;
        if(!correct&&baseline){defects++;Console.WriteLine("REPRODUCED LPC parser "+server);return;}
        Require(correct,"LPC parse: "+server);
        if(!valid)return;
        Require((string)Property(parsed,"PipeHostName")==".","local physical pipe host");
        Require((string)Property(parsed,"PipeName")=="SQLLocal\\"+(instance??"MSSQLSERVER"),"exact SQLLocal instance endpoint");
        Require(!(bool)Property(parsed,"IsSsrpRequired"),"no SQL Browser lookup");
        Require((int)Property(parsed,"Port")==-1,"no TCP port");
    }
    sealed class HandshakeStream : Stream
    {
        readonly Stream transport;byte[] pending=Array.Empty<byte>();int offset;
        internal bool Encapsulate=true;
        internal HandshakeStream(Stream value){transport=value;}
        public override bool CanRead=>true;public override bool CanWrite=>true;public override bool CanSeek=>false;
        public override long Length=>throw new NotSupportedException();
        public override long Position{get=>throw new NotSupportedException();set=>throw new NotSupportedException();}
        public override long Seek(long value,SeekOrigin origin)=>throw new NotSupportedException();
        public override void SetLength(long value)=>throw new NotSupportedException();
        public override void Flush()=>transport.Flush();
        public override Task FlushAsync(CancellationToken token)=>transport.FlushAsync(token);
        public override int Read(byte[] buffer,int start,int count)=>ReadAsync(buffer.AsMemory(start,count)).AsTask().GetAwaiter().GetResult();
        public override void Write(byte[] buffer,int start,int count)=>WriteAsync(buffer.AsMemory(start,count)).AsTask().GetAwaiter().GetResult();
        public override Task<int> ReadAsync(byte[] buffer,int start,int count,CancellationToken token)=>ReadAsync(buffer.AsMemory(start,count),token).AsTask();
        public override Task WriteAsync(byte[] buffer,int start,int count,CancellationToken token)=>WriteAsync(buffer.AsMemory(start,count),token).AsTask();
        public override async ValueTask<int> ReadAsync(Memory<byte> buffer,CancellationToken token=default)
        {
            if(!Encapsulate)return await transport.ReadAsync(buffer,token);
            if(offset==pending.Length)
            {
                var header=new byte[8];await transport.ReadExactlyAsync(header,token);
                int size=BinaryPrimitives.ReadUInt16BigEndian(header.AsSpan(2));Require(header[0]==0x12&&size>8,"TLS handshake PRELOGIN envelope");
                pending=new byte[size-8];offset=0;await transport.ReadExactlyAsync(pending,token);
            }
            int take=Math.Min(buffer.Length,pending.Length-offset);pending.AsMemory(offset,take).CopyTo(buffer);offset+=take;return take;
        }
        public override async ValueTask WriteAsync(ReadOnlyMemory<byte> buffer,CancellationToken token=default)
        {
            if(!Encapsulate){await transport.WriteAsync(buffer,token);return;}
            while(buffer.Length>0)
            {
                int take=Math.Min(buffer.Length,4096-8);var header=new byte[8];header[0]=0x12;header[1]=(byte)(buffer.Length==take?1:0);header[6]=1;
                BinaryPrimitives.WriteUInt16BigEndian(header.AsSpan(2),checked((ushort)(take+8)));
                await transport.WriteAsync(header,token);await transport.WriteAsync(buffer.Slice(0,take),token);buffer=buffer.Slice(take);
            }
        }
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

    static X509Certificate2 Certificate()
    {
        using var rsa=RSA.Create(2048);var request=new CertificateRequest("CN=localhost",rsa,HashAlgorithmName.SHA256,RSASignaturePadding.Pkcs1);
        var names=new SubjectAlternativeNameBuilder();names.AddDnsName("localhost");request.CertificateExtensions.Add(names.Build());
        request.CertificateExtensions.Add(new X509BasicConstraintsExtension(false,false,0,true));
        using var original=request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-1),DateTimeOffset.UtcNow.AddHours(1));
        return new X509Certificate2(original.Export(X509ContentType.Pfx),"",X509KeyStorageFlags.DefaultKeySet);
    }
    static async Task Query(bool asynchronous,bool tls,bool trust,bool baseline)
    {
        string instance="CodexLpc"+Guid.NewGuid().ToString("N").Substring(0,8);
        using var pipe=new NamedPipeServerStream("SQLLocal\\"+instance,PipeDirection.InOut,1,PipeTransmissionMode.Byte,PipeOptions.Asynchronous|PipeOptions.CurrentUserOnly);
        using var stop=new CancellationTokenSource(TimeSpan.FromSeconds(7));
        using var deadline=stop.Token.Register(()=>pipe.Dispose());
        using var certificate=tls?Certificate():null;
        bool accepted=false,encrypted=false;
        var peer=Task.Run(async()=>
        {
            await pipe.WaitForConnectionAsync(stop.Token);accepted=true;
            Stream stream=pipe;SslStream secure=null;
            try
            {
                Require((await ReadPacket(stream))[0]==0x12,"SQLLocal PRELOGIN");
                byte[] prelogin={0,0,11,0,6,1,0,17,0,1,0xff,16,0,1,0,0,0,2};prelogin[^1]=(byte)(tls?1:2);
                await stream.WriteAsync(Packet(prelogin));
                if(tls)
                {
                    var handshake=new HandshakeStream(stream);secure=new SslStream(handshake,true);
                    await secure.AuthenticateAsServerAsync(new SslServerAuthenticationOptions{ServerCertificate=certificate,EnabledSslProtocols=SslProtocols.Tls12},stop.Token);
                    handshake.Encapsulate=false;stream=secure;encrypted=secure.IsEncrypted;
                }
                Require((await ReadPacket(stream))[0]==0x10,"SQLLocal LOGIN7");await stream.WriteAsync(Login());
                var batch=await ReadPacket(stream);Require(batch[0]==1,"SQLLocal SQL batch");
                int offset=8+BinaryPrimitives.ReadInt32LittleEndian(batch.AsSpan(8));Require(Encoding.Unicode.GetString(batch,offset,batch.Length-offset)=="SELECT 42","actual SQLLocal batch");
                await stream.WriteAsync(Rows());
            }
            catch(Exception error)
            {
                Console.WriteLine("PEER LPC termination "+error.GetType().Name);
                try{secure?.Dispose();}catch(Exception cleanup) when(cleanup is ObjectDisposedException||cleanup is IOException){}
                secure=null;pipe.Dispose();throw;
            }
            finally{secure?.Dispose();}
        });
        using var connection=new SqlConnection(new SqlConnectionStringBuilder{DataSource="lpc:localhost\\"+instance,UserID="fixture",Password="fixture",Encrypt=tls,TrustServerCertificate=trust,Pooling=false,ConnectTimeout=3}.ConnectionString);
        Exception failure=null;
        try
        {
            if(asynchronous)await connection.OpenAsync();else connection.Open();
            using var command=new SqlCommand("SELECT 42",connection);
            Require(Convert.ToInt32(asynchronous?await command.ExecuteScalarAsync():command.ExecuteScalar())==42,"public SQLLocal scalar");
        }
        catch(Exception error){failure=error;}
        if(baseline)
        {
            Require(failure!=null&&!accepted,"baseline cannot reach SQLLocal endpoint: "+failure);defects++;stop.Cancel();
            try{await peer;}catch(Exception error) when(stop.IsCancellationRequested&&(error is OperationCanceledException||error is ObjectDisposedException||error is IOException)){}
            Console.WriteLine("REPRODUCED public LPC query async="+asynchronous+" tls="+tls+" exception="+failure.GetType().Name);return;
        }
        if(tls&&!trust)
        {
            Require(accepted&&failure is SqlException&&failure.ToString().Contains("SSL",StringComparison.OrdinalIgnoreCase)&&failure.ToString().Contains("certificate",StringComparison.OrdinalIgnoreCase),"reject untrusted SQLLocal certificate with SSL error");
            try{await peer;}catch(Exception e) when(e is AuthenticationException||e is IOException){}
            Console.WriteLine("PASS LPC untrusted certificate rejected");return;
        }
        Require(failure==null,"public LPC query: "+failure);await peer;Require(accepted&&encrypted==tls,"actual selected IPC endpoint/TLS");
        Console.WriteLine("PASS LPC SQLLocal query async="+asynchronous+" tls="+tls);
    }
    static async Task HandleFields(bool baseline)
    {
        string instance="CodexLpc"+Guid.NewGuid().ToString("N").Substring(0,8);
        object details=Parse("lpc:localhost\\"+instance);
        if(baseline&&Protocol(details)!="LPC"){defects++;Console.WriteLine("REPRODUCED LPC handle selection");return;}
        using var pipe=new NamedPipeServerStream("SQLLocal\\"+instance,PipeDirection.InOut,1,PipeTransmissionMode.Byte,PipeOptions.Asynchronous|PipeOptions.CurrentUserOnly);
        var connected=pipe.WaitForConnectionAsync();
        Type proxyType=typeof(SqlConnection).Assembly.GetType("System.Data.SqlClient.SNI.SNIProxy",true);
        object proxy=proxyType.GetField("Singleton").GetValue(null);
        object handle=proxyType.GetMethod("CreateNpHandle",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(proxy,new object[]{details,DateTime.Now.AddSeconds(3).ToFileTime(),null,false});
        try
        {
            await connected;Type type=handle.GetType();
            Require((uint)type.GetProperty("Status").GetValue(handle)==0,"connected LPC transport");
            Require((string)type.GetField("_targetServer",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(handle)=="localhost","TLS target preserves caller host instead of physical pipe dot");
            Require(type.GetField("_provider",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(handle).ToString()=="SM_PROV","Shared Memory Provider status/error identity");
            var method=proxyType.GetMethod("GetSqlServerSPN",BindingFlags.Static|BindingFlags.NonPublic,null,new[]{DataSource},null);
            string spn=Encoding.UTF8.GetString((byte[])method.Invoke(null,new[]{details}));
            Require(spn.StartsWith("MSSQLSvc/",StringComparison.Ordinal)&&spn.EndsWith(":"+instance.ToLowerInvariant(),StringComparison.Ordinal)&&!spn.Contains('\\'),"LPC SSPI target uses service host/instance rather than pipe path");
        }
        finally{handle.GetType().GetMethod("Dispose").Invoke(handle,null);}
    }
    static async Task BadConnection(string server,bool parallel,bool baseline)
    {
        using var connection=new SqlConnection(new SqlConnectionStringBuilder{DataSource=server,MultiSubnetFailover=parallel,UserID="fixture",Password="fixture",Pooling=false,ConnectTimeout=1}.ConnectionString);
        Exception failure=null;try{await connection.OpenAsync();}catch(Exception e){failure=e;}
        bool correct=parallel ? failure is ArgumentException&&failure.Message.Contains("TCP",StringComparison.OrdinalIgnoreCase) :
            failure is SqlException&&failure.Message.Contains("Shared Memory Provider",StringComparison.OrdinalIgnoreCase);
        if(!correct&&baseline){defects++;Console.WriteLine("REPRODUCED LPC provider error "+server);}
        else Require(correct,"public LPC invalid transport/provider mapping: "+failure);
        Require(connection.State==System.Data.ConnectionState.Closed,"failed LPC connection closed");
    }
    public static int Run(string[] args)
    {
        try{return Execute(args).GetAwaiter().GetResult();}catch(Exception e){Console.Error.WriteLine(e);return 1;}
    }
    static async Task<int> Execute(string[] args)
    {
        bool baseline=Array.IndexOf(args,"--baseline")>=0;
        foreach(string host in new[]{".","(local)","localhost",Environment.MachineName.ToLowerInvariant(),"127.0.0.1","::1","[::1]"})
        {Parser("lpc:"+host,null,true,baseline);Parser("LpC : "+host+"\\OwNeD", "owned",true,baseline);}
        Parser("lpc:.\\MSSQLSERVER","mssqlserver",true,baseline);
        foreach(string server in new[]{"lpc:","lpc:example.invalid","lpc:192.0.2.1","lpc:localhost,1433","lpc:localhost\\","lpc:localhost\\one\\two","lpc:localhost/pipe","lpc:localhost\\..","lpc:localhost\\bad:name"})Parser(server,null,false,baseline);
        await HandleFields(baseline);
        await BadConnection("lpc:example.invalid",false,baseline);
        await BadConnection("lpc:localhost,1433",false,baseline);
        await BadConnection("lpc:localhost\\CodexNotInstalled",true,baseline);
        foreach(bool asynchronous in new[]{false,true})
        {
            await Query(asynchronous,false,false,baseline);
            await Query(asynchronous,true,true,baseline);
        }
        if(!baseline)await Query(true,true,false,false);
        Require(!baseline||defects>0,"baseline must reproduce missing LPC support");
        Console.WriteLine((baseline?"REPRODUCED":"PASS")+" LPC checks="+checks+" defects="+defects);return 0;
    }
    static int Main(string[] args)=>Run(args);
}
