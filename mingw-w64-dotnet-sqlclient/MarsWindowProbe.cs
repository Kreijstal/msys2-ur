// Owned TCP/SMP peer based on MC-SMP's inclusive WNDW limit, independent of SNI.
// https://learn.microsoft.com/en-us/openspecs/windows_protocols/mc-smp/4ada62f7-33c2-45bb-980c-f566f5a6c11a
using System;
using System.Buffers.Binary;
using System.Data.SqlClient;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;

static class MarsWindowProbe
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static async Task<byte[]> ReadTds(Stream stream)
    {
        var h=new byte[8];await stream.ReadExactlyAsync(h);int size=BinaryPrimitives.ReadUInt16BigEndian(h.AsSpan(2));
        Require(size>=8,"TDS header length");var data=new byte[size];h.CopyTo(data,0);await stream.ReadExactlyAsync(data.AsMemory(8));return data;
    }
    static byte[] Tds(byte[] data,bool final=true,byte packetId=1)
    {
        var result=new byte[8+data.Length];result[0]=4;result[1]=(byte)(final?1:0);result[6]=packetId;
        BinaryPrimitives.WriteUInt16BigEndian(result.AsSpan(2),checked((ushort)result.Length));data.CopyTo(result,8);return result;
    }
    static void Done(BinaryWriter writer,long rows){writer.Write((byte)0xfd);writer.Write((ushort)(rows>0?0x10:0));writer.Write((ushort)0);writer.Write(rows);}
    static byte[] Login()
    {
        using var b=new MemoryStream();using var w=new BinaryWriter(b,Encoding.Unicode,true);const string name="OwnedWindowPeer";
        w.Write((byte)0xad);w.Write((ushort)(10+2*name.Length));w.Write((byte)1);w.Write(new byte[]{0x74,0,0,4});
        w.Write((byte)name.Length);w.Write(Encoding.Unicode.GetBytes(name));w.Write(new byte[]{15,0,7,208});Done(w,0);return Tds(b.ToArray());
    }
    record Frame(byte Flags,ushort Sid,uint Sequence,uint Window,byte[] Data);
    static async Task<Frame> ReadFrame(Stream stream)
    {
        var h=new byte[16];await stream.ReadExactlyAsync(h);Require(h[0]==83,"SMP signature");
        uint length=BinaryPrimitives.ReadUInt32LittleEndian(h.AsSpan(4));Require(length>=16&&length<=65536,"bounded SMP length");
        var body=new byte[length-16];await stream.ReadExactlyAsync(body);
        return new Frame(h[1],BinaryPrimitives.ReadUInt16LittleEndian(h.AsSpan(2)),BinaryPrimitives.ReadUInt32LittleEndian(h.AsSpan(8)),BinaryPrimitives.ReadUInt32LittleEndian(h.AsSpan(12)),body);
    }
    static async Task WriteFrame(Stream stream,byte flags,ushort sid,uint sequence,uint window,byte[] data)
    {
        var h=new byte[16];h[0]=83;h[1]=flags;BinaryPrimitives.WriteUInt16LittleEndian(h.AsSpan(2),sid);
        BinaryPrimitives.WriteUInt32LittleEndian(h.AsSpan(4),checked((uint)(16+data.Length)));BinaryPrimitives.WriteUInt32LittleEndian(h.AsSpan(8),sequence);BinaryPrimitives.WriteUInt32LittleEndian(h.AsSpan(12),window);
        await stream.WriteAsync(h.AsMemory(0,7));await stream.WriteAsync(h.AsMemory(7));
        if(data.Length>0){await stream.WriteAsync(data.AsMemory(0,3));await stream.WriteAsync(data.AsMemory(3));}
    }
    static async Task Peer(TcpListener listener)
    {
        using var client=await listener.AcceptTcpClientAsync();using var stream=client.GetStream();
        Require((await ReadTds(stream))[0]==0x12,"prelogin");
        await stream.WriteAsync(Tds(new byte[]{0,0,16,0,6,1,0,22,0,1,4,0,23,0,1,0xff,15,0,7,208,0,0,2,1}));
        Require((await ReadTds(stream))[0]==0x10,"LOGIN7");await stream.WriteAsync(Login());
        Frame syn=await ReadFrame(stream);Require(syn.Flags==1&&syn.Sequence==0,"initial SYN");
        uint permitted=4,received=0,receiveWindow=syn.Window;int stoppedWindows=0,acknowledgments=0;
        var opened=new Dictionary<ushort,uint>{{syn.Sid,syn.Window}};ushort? active=null;
        await WriteFrame(stream,2,syn.Sid,0,permitted,Array.Empty<byte>());
        using var batch=new MemoryStream();
        while(true)
        {
            Frame frame;
            try{frame=await ReadFrame(stream).WaitAsync(TimeSpan.FromSeconds(3));}
            catch(TimeoutException){Console.Error.WriteLine("SMP inclusive-window failure: received="+received+" permitted="+permitted);throw new Exception("SMP inclusive-window failure: received "+received+" DATA packets; sequence "+(received+1)+" is permitted by WNDW="+permitted+" but was not transmitted");}
            if(frame.Flags==1){Require(frame.Sequence==0&&!opened.ContainsKey(frame.Sid),"unique additional SYN");opened.Add(frame.Sid,frame.Window);await WriteFrame(stream,2,frame.Sid,0,permitted,Array.Empty<byte>());continue;}
            if(active is null){active=frame.Sid;receiveWindow=opened[frame.Sid];}
            Require(frame.Sid==active&&frame.Flags==8&&frame.Sequence==received+1&&frame.Sequence<=permitted,"sequential DATA within inclusive advertised window: flags="+frame.Flags+" SID="+frame.Sid+" seq="+frame.Sequence+" previous="+received+" WNDW="+permitted);
            received=frame.Sequence;receiveWindow=frame.Window;Require(frame.Data.Length>=8&&frame.Data[0]==1,"TDS batch fragment");
            batch.Write(frame.Data,8,frame.Data.Length-8);bool complete=(frame.Data[1]&1)!=0;
            if(received==permitted&&!complete)
            {
                await Task.Delay(100);Require(client.Available==0,"sender must stop beyond inclusive window boundary");stoppedWindows++;
                permitted+=4;await WriteFrame(stream,2,active.Value,0,permitted,Array.Empty<byte>());
            }
            if(complete)break;
        }
        var bytes=batch.ToArray();int headerLength=BinaryPrimitives.ReadInt32LittleEndian(bytes);
        string query=Encoding.Unicode.GetString(bytes,headerLength,bytes.Length-headerLength);
        Require(query.StartsWith("SELECT 42 AS Fixture",StringComparison.Ordinal)&&query.Length>30000&&received>=8&&stoppedWindows>=2,"complete large SQL batch across multiple send windows");
        // Ten response fragments require the client to consume data and grant receive credits.
        for(uint sequence=1;sequence<=10;sequence++)
        {
            while(sequence>receiveWindow)
            {
                Frame ack=await ReadFrame(stream).WaitAsync(TimeSpan.FromSeconds(3));
                Require(ack.Sid==active&&ack.Flags==2&&ack.Sequence==received&&ack.Window>receiveWindow,"ACK advances receive credits with stable last-send sequence");
                receiveWindow=ack.Window;acknowledgments++;
            }
            using var part=new MemoryStream();using(var writer=new BinaryWriter(part,Encoding.Unicode,true))
            {
                if(sequence==1){writer.Write((byte)0x81);writer.Write((ushort)1);writer.Write((uint)0);writer.Write((ushort)0);writer.Write((byte)0x38);writer.Write((byte)7);writer.Write(Encoding.Unicode.GetBytes("Fixture"));}
                writer.Write((byte)0xd1);writer.Write(41+(int)sequence);if(sequence==10)Done(writer,10);
            }
            await WriteFrame(stream,8,active.Value,sequence,permitted,Tds(part.ToArray(),sequence==10,(byte)sequence));
        }
        Require(acknowledgments>=2,"multiple client receive-window grants");
        Console.WriteLine("PASS MC-SMP inclusive WNDW boundary: "+received+" query DATA frames, "+stoppedWindows+" verified sender stalls/resumes,10 response frames and "+acknowledgments+" client ACK window grants");
        // Wait for the public reader to consume DONE and close its session/connection.
        while(true)
        {
            Frame frame;
            try{frame=await ReadFrame(stream).WaitAsync(TimeSpan.FromSeconds(5));}
            catch(EndOfStreamException){break;}
            catch(IOException){break;}
            Require(opened.ContainsKey(frame.Sid)&&(frame.Flags==2||frame.Flags==4),"terminal ACK/FIN");
            if(frame.Flags==4&&frame.Sid==active)break;
        }
    }
    public static async Task Run()
    {
        var listener=new TcpListener(IPAddress.Loopback,0);listener.Start();Task peer=Peer(listener);
        SqlConnection connection=null;
        try
        {
            int port=((IPEndPoint)listener.LocalEndpoint).Port;
            connection=new SqlConnection("Server=tcp:127.0.0.1,"+port+";User ID=fixture;Password=fixture;Encrypt=false;Pooling=false;MultipleActiveResultSets=true;Packet Size=4096;Connect Timeout=5");
            await connection.OpenAsync();
            using(var command=connection.CreateCommand())
            {
                command.CommandTimeout=8;command.CommandText="SELECT 42 AS Fixture"+new string(' ',50000);
                Task<SqlDataReader> pending=command.ExecuteReaderAsync();
                if(await Task.WhenAny(pending,peer)==peer&&peer.IsFaulted)await peer;
                using var reader=await pending;int count=0;
                while(await reader.ReadAsync()){Require(reader.GetInt32(0)==42+count,"flow-controlled ordered result row");count++;if(count==3){GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();}}
                Require(count==10,"all10 rows and DONE");
            }
            connection.Dispose();connection=null;
            await peer.WaitAsync(TimeSpan.FromSeconds(6));
            Console.WriteLine("PASS public SqlClient MARS large-batch send/receive flow control, fragmented TDS/SMP, ordered async rows, compacting GC and DONE");
        }
        catch{if(peer.IsFaulted)Console.Error.WriteLine(peer.Exception);throw;}
        finally
        {
            listener.Stop();
            // A failed peer can leave the old SNI send queue blocked inside Close.
            // This isolated test process exits on failure; dispose normally after success.
            if(connection!=null&&peer.IsCompletedSuccessfully)connection.Dispose();
        }
    }
}
