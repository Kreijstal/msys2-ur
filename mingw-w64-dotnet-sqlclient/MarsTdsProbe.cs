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

static class MarsTdsProbe
{
    static void Require(bool value, string message) { if (!value) throw new Exception(message); }
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
    static byte[] Rows(int value)
    {
        using var bytes = new MemoryStream(); using var writer = new BinaryWriter(bytes, Encoding.Unicode, true);
        writer.Write((byte)0x81); writer.Write((ushort)1); writer.Write((uint)0); writer.Write((ushort)0); writer.Write((byte)0x38);
        const string column = "Fixture";
        writer.Write((byte)column.Length); writer.Write(Encoding.Unicode.GetBytes(column));
        for (int i=0; i<2; i++) { writer.Write((byte)0xd1); writer.Write(value+i); }
        Done(writer, 2); return Packet(bytes.ToArray());
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
    static async Task Peer(TcpListener listener, Task applicationClosing)
    {
        using var client = await listener.AcceptTcpClientAsync(); using var stream = client.GetStream();
        byte[] prelogin = await ReadPacket(stream); Require(prelogin[0] == 0x12, "MARS prelogin");
        // VERSION, ENCRYPTION=NOT_SUPPORTED, MARS=ON.
        await stream.WriteAsync(Packet(new byte[]{0,0,16,0,6,1,0,22,0,1,4,0,23,0,1,0xff,15,0,7,208,0,0,2,1}));
        Require((await ReadPacket(stream))[0] == 0x10, "MARS LOGIN7");
        await stream.WriteAsync(Login());
        var sequence = new Dictionary<ushort, uint>(); var queried = new HashSet<ushort>();
        int requests = 0, fins = 0;
        while (true)
        {
            byte[] header = new byte[16];
            int first;
            try { first = await stream.ReadAsync(header.AsMemory(0, 1)); }
            catch (IOException) when (applicationClosing.IsCompleted && requests == 3 && queried.Count >= 2 && fins > 0) { break; }
            if (first == 0) break;
            await stream.ReadExactlyAsync(header.AsMemory(1));
            Require(header[0] == 83, "SMP signature");
            byte flags = header[1]; ushort id = BinaryPrimitives.ReadUInt16LittleEndian(header.AsSpan(2));
            uint length = BinaryPrimitives.ReadUInt32LittleEndian(header.AsSpan(4));
            uint received = BinaryPrimitives.ReadUInt32LittleEndian(header.AsSpan(8));
            Require(length >= 16 && length <= 32768, "SMP frame length");
            byte[] data = new byte[length-16]; await stream.ReadExactlyAsync(data);
            if (flags == 1)
            {
                Require(length == 16 && received == 0 && !sequence.ContainsKey(id), "new SMP SYN");
                sequence.Add(id, 0); await Frame(stream, 2, id, 0, 16, Array.Empty<byte>());
            }
            else if (flags == 8)
            {
                Require(sequence.ContainsKey(id) && data.Length >= 12 && data[0] == 1, "SMP DATA carries a SQL batch");
                int offset = 8+BinaryPrimitives.ReadInt32LittleEndian(data.AsSpan(8));
                Require(offset >= 12 && offset <= data.Length, "MARS TDS all-headers length");
                string query = Encoding.Unicode.GetString(data, offset, data.Length-offset);
                int value = query.Contains("SELECT 42 AS Fixture", StringComparison.Ordinal) ? 42 :
                    query.Contains("SELECT 84 AS Fixture", StringComparison.Ordinal) ? 84 : 0;
                Require(value != 0, "expected fixture SQL batch: " + query);
                queried.Add(id); requests++;
                sequence[id]++; await Frame(stream, 8, id, sequence[id], received+16, Rows(value));
            }
            else if (flags == 2) { Require(length == 16 && sequence.ContainsKey(id), "known SMP ACK"); }
            else if (flags == 4)
            {
                Require(length == 16 && sequence.ContainsKey(id), "known SMP FIN");
                fins++;
                // Closing the whole non-pooled connection aborts the physical
                // socket without waiting for logical-session FIN responses.
                if (!applicationClosing.IsCompleted)
                    await Frame(stream, 4, id, sequence[id], received+16, Array.Empty<byte>());
            }
            else throw new Exception("unexpected SMP flags " + flags);
        }
        Require(applicationClosing.IsCompleted && queried.Count >= 2 && requests == 3 && fins > 0,
            "completed application checks, multiple SMP sessions, three batches and session FIN");
        Console.WriteLine("PASS independent SMP peer: " + queried.Count + " query sessions, three batches, fragmented headers/payloads and " + fins + " FINs");
    }
    public static async Task Run()
    {
        var closing = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        var listener = new TcpListener(IPAddress.Loopback, 0); listener.Start(); var peer = Peer(listener, closing.Task);
        try
        {
            int port = ((IPEndPoint)listener.LocalEndpoint).Port;
            using (var connection = new SqlConnection("Server=tcp:127.0.0.1,"+port+";User ID=fixture;Password=fixture;Encrypt=false;Pooling=false;MultipleActiveResultSets=true;Connect Timeout=5"))
            {
                await connection.OpenAsync();
                using var first = connection.CreateCommand(); first.CommandText = "SELECT 42 AS Fixture";
                using var second = connection.CreateCommand(); second.CommandText = "SELECT 84 AS Fixture";
                using (var a = await first.ExecuteReaderAsync())
                {
                    Require(await a.ReadAsync() && a.GetInt32(0) == 42, "first MARS reader row 1");
                    using var b = await second.ExecuteReaderAsync();
                    Require(await b.ReadAsync() && b.GetInt32(0) == 84, "second reader while first remains open");
                    GC.Collect(2, GCCollectionMode.Forced, true, true); GC.WaitForPendingFinalizers();
                    Require(await a.ReadAsync() && a.GetInt32(0) == 43, "retained first reader row 2 after GC");
                    Require(await b.ReadAsync() && b.GetInt32(0) == 85, "second reader row 2 after GC");
                    Require(!await a.ReadAsync() && !await b.ReadAsync(), "independent reader DONE");
                }
                Require(Convert.ToInt32(first.ExecuteScalar()) == 42, "reuse after both readers are disposed");
                closing.SetResult(true);
            }
            await peer.WaitAsync(TimeSpan.FromSeconds(5));
            Console.WriteLine("PASS public Release SqlClient MARS: simultaneous readers, interleaved rows, compacting GC, independent DONE and session reuse");
        }
        catch { if (peer.IsFaulted) Console.Error.WriteLine(peer.Exception); throw; }
        finally { listener.Stop(); }
    }
}
