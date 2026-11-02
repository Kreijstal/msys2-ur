// Private loopback protocol peer. This does not stand in for a SQL Server
// interoperability suite or establish feature parity with native Windows SNI.
using System;
using System.Buffers.Binary;
using System.Data;
using System.Data.SqlClient;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;

static class ManagedTdsProbe
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static async Task<(byte Type,byte[] Payload)> Read(Stream stream)
    {
        byte[] header=new byte[8];await stream.ReadExactlyAsync(header);
        int length=BinaryPrimitives.ReadUInt16BigEndian(header.AsSpan(2));
        Require(length>=8 && (header[1]&1)!=0,"single complete TDS packet");
        byte[] payload=new byte[length-8];await stream.ReadExactlyAsync(payload);return(header[0],payload);
    }
    static async Task Write(Stream stream,byte[] payload)
    {
        byte[] header={4,1,0,0,0,0,1,0};
        BinaryPrimitives.WriteUInt16BigEndian(header.AsSpan(2),checked((ushort)(payload.Length+8)));
        await stream.WriteAsync(header);await stream.WriteAsync(payload);await stream.FlushAsync();
    }
    static void Done(BinaryWriter writer,bool rows=false)
    {writer.Write((byte)0xfd);writer.Write((ushort)(rows?0x10:0));writer.Write((ushort)0);writer.Write((long)(rows?1:0));}
    static byte[] Login()
    {
        using var bytes=new MemoryStream();using var writer=new BinaryWriter(bytes,Encoding.Unicode,true);
        const string name="SourceFixture";
        writer.Write((byte)0xad);writer.Write((ushort)(10+2*name.Length));
        writer.Write((byte)1);writer.Write(new byte[]{0x74,0,0,4});writer.Write((byte)name.Length);writer.Write(Encoding.Unicode.GetBytes(name));
        writer.Write(new byte[]{15,0,7,208});Done(writer);return bytes.ToArray();
    }
    static byte[] Result()
    {
        using var bytes=new MemoryStream();using var writer=new BinaryWriter(bytes,Encoding.Unicode,true);
        const string column="Fixture";
        writer.Write((byte)0x81);writer.Write((ushort)1);writer.Write((uint)0);writer.Write((ushort)0);writer.Write((byte)0x38);
        writer.Write((byte)column.Length);writer.Write(Encoding.Unicode.GetBytes(column));
        writer.Write((byte)0xd1);writer.Write(42);Done(writer,true);return bytes.ToArray();
    }
    static async Task Peer(TcpListener listener)
    {
        using var client=await listener.AcceptTcpClientAsync();using var stream=client.GetStream();
        var prelogin=await Read(stream);Require(prelogin.Type==0x12,"prelogin packet");
        // VERSION, ENCRYPTION=NOT_SUPPORTED, MARS=OFF. This fixture only checks
        // explicit Encrypt=false SQL authentication over a private socket.
        await Write(stream,new byte[]{0,0,16,0,6,1,0,22,0,1,4,0,23,0,1,0xff,15,0,7,208,0,0,2,0});
        var login=await Read(stream);Require(login.Type==0x10&&login.Payload.Length>=94,"LOGIN7 packet");
        await Write(stream,Login());
        for(int i=0;i<2;i++)
        {
            var batch=await Read(stream);Require(batch.Type==1,"SQL batch packet");
            int offset=BinaryPrimitives.ReadInt32LittleEndian(batch.Payload);
            Require(offset>=4&&offset<=batch.Payload.Length,"TDS all-headers length");
            string query=Encoding.Unicode.GetString(batch.Payload,offset,batch.Payload.Length-offset);
            Require(query.Contains("SELECT 42 AS Fixture",StringComparison.OrdinalIgnoreCase),"SQL batch contents");
            await Write(stream,Result());
        }
    }
    static async Task Main()
    {
        Environment.SetEnvironmentVariable("System.Data.SqlClient.UseManagedSNIOnWindows","true");
        var listener=new TcpListener(IPAddress.Loopback,0);listener.Start();
        var peer=Peer(listener);
        try
        {
            int port=((IPEndPoint)listener.LocalEndpoint).Port;
            using var connection=new SqlConnection("Server=tcp:127.0.0.1,"+port+";User ID=fixture;Password=fixture;Encrypt=false;Pooling=false;Connect Timeout=5");
            await connection.OpenAsync();Require(connection.State==ConnectionState.Open,"managed SNI connection");
            using(var command=connection.CreateCommand())
            {command.CommandText="SELECT 42 AS Fixture";Require(Convert.ToInt32(command.ExecuteScalar())==42,"synchronous scalar");}
            using(var command=connection.CreateCommand())
            {
                command.CommandText="SELECT 42 AS Fixture";
                using var reader=await command.ExecuteReaderAsync();
                Require(await reader.ReadAsync()&&reader.GetInt32(0)==42&&reader.GetName(0)=="Fixture","async reader row/metadata");
                Require(!await reader.ReadAsync(),"reader DONE");
            }
            await peer.WaitAsync(TimeSpan.FromSeconds(5));connection.Close();
            foreach(System.Diagnostics.ProcessModule module in System.Diagnostics.Process.GetCurrentProcess().Modules)
                Require(!module.ModuleName.Equals("sni.dll",StringComparison.OrdinalIgnoreCase),"no prebuilt SNI module");
            Console.WriteLine("PASS upstream Windows managed SNI debug path: TCP prelogin/LOGIN7, sync scalar, async reader/schema/DONE; no sni.dll");
            Console.WriteLine("Prototype only: native feature parity, TLS, auth, MARS, named pipes, LocalDB, FILESTREAM and database interoperability remain open.");
        }
        catch {if(peer.IsFaulted)Console.Error.WriteLine(peer.Exception);throw;}
        finally {listener.Stop();}
    }
}
