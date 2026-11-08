// Independent loopback TDS/SMP fixture. This exercises public SqlClient MARS
// readers; it is not a SQL Server database engine or a full SMP conformance suite.
using System;
using System.Buffers.Binary;
using System.Collections.Generic;
using System.Data.SqlClient;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;
using System.Threading;
using System.Diagnostics;
using System.Linq;
using System.Net.Security;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;

internal static class MarsCancelChecks
{
    static int checks;
    static void Require(bool value, string message) { Interlocked.Increment(ref checks); if (!value) throw new Exception(message); }
    // MS-TDS wraps TLS handshake bytes in PRELOGIN packets; application TLS
    // records use the transport directly after AuthenticateAsServer completes.
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
        byte[] header = new byte[8]; await stream.ReadExactlyAsync(header);
        Require((header[1]&1) != 0, "fixture expects one complete TDS message");
        int length = BinaryPrimitives.ReadUInt16BigEndian(header.AsSpan(2));
        Require(length >= 8, "valid TDS packet length");
        byte[] data = new byte[length]; header.CopyTo(data, 0);
        await stream.ReadExactlyAsync(data.AsMemory(8)); return data;
    }
    static byte[] Packet(byte[] data)
    {
        byte[] result = new byte[data.Length+8]; result[0] = 4; result[1] = 1; result[6] = 1;
        BinaryPrimitives.WriteUInt16BigEndian(result.AsSpan(2), checked((ushort)result.Length));
        data.CopyTo(result, 8); return result;
    }
    static void Done(BinaryWriter writer, long count)
    { writer.Write((byte)0xfd); writer.Write((ushort)(count != 0 ? 0x10 : 0)); writer.Write((ushort)0); writer.Write(count); }
    static byte[] Login()
    {
        using var bytes = new MemoryStream(); using var writer = new BinaryWriter(bytes, Encoding.Unicode, true);
        const string name = "SourceMarsFixture";
        writer.Write((byte)0xad); writer.Write((ushort)(10+2*name.Length));
        writer.Write((byte)1); writer.Write(new byte[]{0x74,0,0,4});
        writer.Write((byte)name.Length); writer.Write(Encoding.Unicode.GetBytes(name));
        writer.Write(new byte[]{15,0,7,208}); Done(writer, 0); return Packet(bytes.ToArray());
    }
    static byte[] Rows(int value, bool stalled=false)
    {
        using var bytes = new MemoryStream(); using var writer = new BinaryWriter(bytes, Encoding.Unicode, true);
        writer.Write((byte)0x81); writer.Write((ushort)1); writer.Write((uint)0); writer.Write((ushort)0); writer.Write((byte)0x38);
        const string column = "Fixture";
        writer.Write((byte)column.Length); writer.Write(Encoding.Unicode.GetBytes(column));
        for (int i=0; i<(stalled?1:2); i++) { writer.Write((byte)0xd1); writer.Write(value+i); }
        if(!stalled)Done(writer, 2);var packet=Packet(bytes.ToArray());if(stalled)packet[1]=0;return packet;
    }
    static async Task Frame(Stream stream, byte flags, ushort id, uint sequence, uint highwater, byte[] data)
    {
        byte[] header = new byte[16]; header[0] = 83; header[1] = flags;
        BinaryPrimitives.WriteUInt16LittleEndian(header.AsSpan(2), id);
        BinaryPrimitives.WriteUInt32LittleEndian(header.AsSpan(4), checked((uint)(16+data.Length)));
        BinaryPrimitives.WriteUInt32LittleEndian(header.AsSpan(8), sequence);
        BinaryPrimitives.WriteUInt32LittleEndian(header.AsSpan(12), highwater);
        // Deliberately fragment the SMP header and TDS payload across writes.
        await stream.WriteAsync(header.AsMemory(0, 5)); await Task.Delay(1);
        await stream.WriteAsync(header.AsMemory(5));
        if (data.Length > 0)
        {
            await stream.WriteAsync(data.AsMemory(0, 3)); await Task.Delay(1);
            await stream.WriteAsync(data.AsMemory(3));
        }
        await stream.FlushAsync();
    }
    static byte[] AttentionAck()
    {
        using var bytes=new MemoryStream();using var writer=new BinaryWriter(bytes);
        writer.Write((byte)0xfd);writer.Write((ushort)0x20);writer.Write((ushort)0);writer.Write((long)0);
        var packet=Packet(bytes.ToArray());packet[6]=2;return packet;
    }
    static byte[] ServerError()
    {
        const string message="Owned MARS error";
        using var bytes=new MemoryStream();using var writer=new BinaryWriter(bytes,Encoding.Unicode,true);
        writer.Write((byte)0xaa);writer.Write((ushort)(14+2*message.Length));writer.Write(50001);writer.Write((byte)1);writer.Write((byte)16);
        writer.Write((ushort)message.Length);writer.Write(Encoding.Unicode.GetBytes(message));writer.Write((byte)0);writer.Write((byte)0);writer.Write((uint)1);
        writer.Write((byte)0xfd);writer.Write((ushort)2);writer.Write((ushort)0);writer.Write((long)0);
        var packet=Packet(bytes.ToArray());packet[6]=2;return packet;
    }
    static async Task Peer(TcpListener listener,Task applicationClosing,string mode,X509Certificate2 certificate)
    {
        using var client=await listener.AcceptTcpClientAsync();using var network=client.GetStream();Stream stream=network;
        Require((await ReadPacket(stream))[0]==0x12,"MARS prelogin");
        var prelogin=new byte[]{0,0,16,0,6,1,0,22,0,1,4,0,23,0,1,0xff,15,0,7,208,0,0,2,1};
        prelogin[^2]=(byte)(certificate==null?2:1);await stream.WriteAsync(Packet(prelogin));
        using var handshake=certificate==null?null:new HandshakeStream(network);
        using var tls=certificate==null?null:new SslStream(handshake,true);
        if(tls!=null)
        {
            await tls.AuthenticateAsServerAsync(new SslServerAuthenticationOptions{ServerCertificate=certificate,EnabledSslProtocols=SslProtocols.Tls12,ClientCertificateRequired=false});
            handshake.Encapsulate=false;stream=tls;
            Require(tls.IsAuthenticated&&tls.IsEncrypted&&tls.SslProtocol==SslProtocols.Tls12,"authenticated encrypted TLS 1.2 transport");
            Console.WriteLine("PEER TLS 1.2 encrypted MARS mode="+mode);
        }
        Require((await ReadPacket(stream))[0]==0x10,"MARS LOGIN7");await stream.WriteAsync(Login());
        var sequence=new Dictionary<ushort,uint>();ushort? cancelled=null;int requests=0,attention=0,fins=0;
        while(true)
        {
            var header=new byte[16];int first;
            try{first=await stream.ReadAsync(header.AsMemory(0,1));}
            catch(IOException)when(applicationClosing.IsCompleted){break;}
            if(first==0)break;await stream.ReadExactlyAsync(header.AsMemory(1));
            Require(header[0]==83,"SMP signature");byte flags=header[1];ushort id=BinaryPrimitives.ReadUInt16LittleEndian(header.AsSpan(2));
            uint length=BinaryPrimitives.ReadUInt32LittleEndian(header.AsSpan(4)),received=BinaryPrimitives.ReadUInt32LittleEndian(header.AsSpan(8));
            Require(length>=16&&length<=32768,"bounded SMP frame");var data=new byte[length-16];await stream.ReadExactlyAsync(data);
            if(flags==1){Require(!sequence.ContainsKey(id)&&received==0,"new SYN");sequence.Add(id,0);await Frame(stream,2,id,0,32,Array.Empty<byte>());}
            else if(flags==8)
            {
                Require(sequence.ContainsKey(id)&&data.Length>=8,"known SMP session with TDS data");
                if(data[0]==6)
                {
                    Require(cancelled==id&&data.Length==8&&attention==0,"one ATTENTION on the stalled session");attention++;
                    sequence[id]++;await Frame(stream,8,id,sequence[id],received+32,AttentionAck());
                    Console.WriteLine("PEER attention SID="+id+" DONE_ATTN acknowledged");continue;
                }
                Require(data[0]==1&&data.Length>=12,"SQL batch data");int offset=8+BinaryPrimitives.ReadInt32LittleEndian(data.AsSpan(8));
                Require(offset>=12&&offset<=data.Length,"SQL all-headers length");string query=Encoding.Unicode.GetString(data,offset,data.Length-offset);
                int value=query.Contains("SELECT 42 AS Fixture",StringComparison.Ordinal)?42:query.Contains("SELECT 84 AS Fixture",StringComparison.Ordinal)?84:query.Contains("SELECT 126 AS Fixture",StringComparison.Ordinal)?126:0;
                Require(value!=0,"known owned batch");requests++;if(value==42){Require(cancelled==null,"one stalled batch");cancelled=id;}
                sequence[id]++;await Frame(stream,8,id,sequence[id],received+32,Rows(value,value==42));
                if(value==84&&mode=="error")
                {
                    Require(cancelled.HasValue,"stalled reader available for owned server error");
                    ushort failed=cancelled.Value;sequence[failed]++;await Frame(stream,8,failed,sequence[failed],received+32,ServerError());
                    Console.WriteLine("PEER error 50001 isolated to SID="+failed);
                }
            }
            else if(flags==2)Require(sequence.ContainsKey(id)&&length==16,"known ACK");
            else if(flags==4){Require(sequence.ContainsKey(id)&&length==16,"known FIN");fins++;if(!applicationClosing.IsCompleted)await Frame(stream,4,id,sequence[id],received+32,Array.Empty<byte>());}
            else throw new Exception("unexpected SMP flags "+flags);
        }
        Require(applicationClosing.IsCompleted&&requests==3&&attention==(mode=="error"?0:1)&&fins>0,"three queries, expected ATTENTION count and session close");
        Console.WriteLine("PASS peer session isolation mode="+mode+" batches="+requests+" ATTENTION="+attention+" FINs="+fins);
    }
    public static async Task Run(string mode,X509Certificate2 certificate)
    {
        var closing=new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        var listener=new TcpListener(IPAddress.Loopback,0);listener.Start();var peer=Peer(listener,closing.Task,mode,certificate);
        SqlConnection connection=null;
        try
        {
            int port=((IPEndPoint)listener.LocalEndpoint).Port;
            connection=new SqlConnection("Server=tcp:127.0.0.1,"+port+";User ID=fixture;Password=fixture;Encrypt="+(certificate==null?"false":"true")+";TrustServerCertificate=true;Pooling=false;MultipleActiveResultSets=true;Connect Timeout=5");
            await connection.OpenAsync();
            var first=connection.CreateCommand();first.CommandText="SELECT 42 AS Fixture";first.CommandTimeout=mode=="timeout"?1:5;
            var second=connection.CreateCommand();second.CommandText="SELECT 84 AS Fixture";second.CommandTimeout=5;
            var a=await first.ExecuteReaderAsync();Require(await a.ReadAsync()&&a.GetInt32(0)==42,"stalled reader first row");
            var b=await second.ExecuteReaderAsync();Require(await b.ReadAsync()&&b.GetInt32(0)==84,"independent reader first row");
            using var cancellation=new CancellationTokenSource();
            var pending=mode=="token"?a.ReadAsync(cancellation.Token):a.ReadAsync();
            if(mode=="command")first.Cancel();else if(mode=="token")cancellation.Cancel();
            bool cancelled=false;
            try{await pending.WaitAsync(TimeSpan.FromSeconds(8));}
            catch(SqlException error){cancelled=true;Require(error.Number==(mode=="error"?50001:mode=="timeout"?-2:0),"Expected native public cancellation/timeout error code");Console.WriteLine("CLIENT mode="+mode+" SqlException number="+error.Number);}
            Require(cancelled,"Cancellation or timeout surfaces failure on the pending reader");a.Dispose();first.Dispose();
            Require(connection.State==System.Data.ConnectionState.Open,"physical connection survives cancelled logical session");
            GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();
            Require(await b.ReadAsync()&&b.GetInt32(0)==85&&!await b.ReadAsync(),"independent reader completes after cancellation/GC");b.Dispose();second.Dispose();
            var recovery=connection.CreateCommand();recovery.CommandText="SELECT 126 AS Fixture";recovery.CommandTimeout=5;
            Require(Convert.ToInt32(await recovery.ExecuteScalarAsync())==126,"query succeeds after cancellation acknowledgement");recovery.Dispose();
            closing.SetResult(true);connection.Dispose();connection=null;await peer.WaitAsync(TimeSpan.FromSeconds(5));
            Console.WriteLine("PASS MARS independent-reader/recovery mode="+mode+" TLS="+(certificate!=null));
        }
        catch{if(peer.IsFaulted)Console.Error.WriteLine(peer.Exception);throw;}
        finally{listener.Stop();}
    }
    private static async Task<int> Main()
    {
        try
        {
            using var key=RSA.Create(2048);var request=new CertificateRequest("CN=localhost",key,HashAlgorithmName.SHA256,RSASignaturePadding.Pkcs1);
            var names=new SubjectAlternativeNameBuilder();names.AddDnsName("localhost");names.AddIpAddress(IPAddress.Loopback);request.CertificateExtensions.Add(names.Build());
            request.CertificateExtensions.Add(new X509BasicConstraintsExtension(false,false,0,true));
            using var generated=request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-1),DateTimeOffset.UtcNow.AddHours(1));
            // Schannel needs a provider-backed key for server credentials. A
            // default-key-set import owns a temporary key deleted on disposal;
            // no trust store or PersistKeySet flag is used.
            using var certificate=new X509Certificate2(generated.Export(X509ContentType.Pfx),"",X509KeyStorageFlags.DefaultKeySet);
            foreach(bool encrypted in new[]{false,true})foreach(var mode in new[]{"command","token","timeout","error"})await Run(mode,encrypted?certificate:null);
            var implementation=typeof(SqlConnection).Assembly;
            Require(Path.GetFullPath(implementation.Location).StartsWith(Path.GetFullPath(AppContext.BaseDirectory),StringComparison.OrdinalIgnoreCase),"Consumer uses its own restored or bundled source SqlClient");
            using(var process=Process.GetCurrentProcess())
                Require(!process.Modules.Cast<ProcessModule>().Any(module=>module.ModuleName.Equals("sni.dll",StringComparison.OrdinalIgnoreCase)||module.FileName.Contains("\\Microsoft.NET\\Framework",StringComparison.OrdinalIgnoreCase)),"No proprietary SNI or Framework helper loaded");
            Console.WriteLine("SOURCE_SQLCLIENT "+implementation.Location);
            Console.WriteLine("PASS "+checks+" MARS command/token/timeout/error isolation and recovery checks with plaintext and TLS");return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
}
