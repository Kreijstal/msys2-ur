using System;
using System.Collections.Generic;
using System.Data;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Reflection;
using System.Reflection.Emit;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Xml.Linq;

internal static class CompleteFrameworkProbe
{
    private static void Check(bool value, string message)
    {
        if (!value) throw new Exception(message);
        Console.WriteLine("PASS " + message);
    }

    private static async Task Main()
    {
        Check(Environment.Version == new Version(10, 0, 5), "actual CLR 10.0.5");
        var dictionary = new OrderedDictionary<string, int>();
        dictionary.Add("second", 2); dictionary.Insert(0, "first", 1);
        Check(dictionary.GetAt(0).Key == "first", ".NET 10 ordered collection API");
        var payload = new Dictionary<string, string> { ["λ"] = "😀 source10" };
        string json = JsonSerializer.Serialize(payload);
        Check(JsonSerializer.Deserialize<Dictionary<string, string>>(json)!["λ"] == payload["λ"],
            "JSON reflection serialization and Unicode encoding");
        var xml = XElement.Parse("<root><value>λ😀</value></root>");
        Check(xml.Element("value")!.Value == "λ😀", "XML parser and LINQ to XML");
        var table = new DataTable("source10"); table.Columns.Add("value", typeof(int));
        table.Rows.Add(3); table.Rows.Add(7);
        Check(Convert.ToInt64(table.Compute("SUM(value)", "")) == 10, "DataTable expression engine");
        Check(Regex.IsMatch("λ123", "^\\p{L}\\d+$", RegexOptions.NonBacktracking),
            "regular expression nonbacktracking engine");
        Check(Microsoft.VisualBasic.Strings.StrReverse("source10") == "01ecruos",
            "original Visual Basic implementation");
        var method = new DynamicMethod("Source10Add", typeof(int), new[] { typeof(int), typeof(int) });
        ILGenerator il = method.GetILGenerator(); il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Ldarg_1);
        il.Emit(OpCodes.Add); il.Emit(OpCodes.Ret);
        Check(((Func<int, int, int>)method.CreateDelegate(typeof(Func<int, int, int>)))(19, 23) == 42,
            "Reflection.Emit dynamic method and JIT");
        byte[] bytes = Encoding.UTF8.GetBytes("source10 λ😀");
        Check(SHA256.HashData(bytes).Length == 32, "Windows native SHA256");
        using (RSA rsa = RSA.Create(2048))
        {
            byte[] signature = rsa.SignData(bytes, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
            Check(rsa.VerifyData(bytes, signature, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1),
                "Windows native RSA signature round trip");
        }
        string directory = Path.Combine(Path.GetTempPath(), "source10 λ " + Guid.NewGuid());
        Directory.CreateDirectory(directory);
        try
        {
            string file = Path.Combine(directory, "😀.txt");
            await File.WriteAllTextAsync(file, "λ😀");
            Check(await File.ReadAllTextAsync(file) == "λ😀", "async Unicode filesystem I/O");
        }
        finally { Directory.Delete(directory, true); }
        var listener = new TcpListener(IPAddress.Loopback, 0); listener.Start();
        try
        {
            int port = ((IPEndPoint)listener.LocalEndpoint).Port;
            Task server = Task.Run(async () =>
            {
                using TcpClient connection = await listener.AcceptTcpClientAsync();
                using NetworkStream stream = connection.GetStream();
                using var reader = new StreamReader(stream, Encoding.ASCII, false, 1024, true);
                while (!string.IsNullOrEmpty(await reader.ReadLineAsync())) { }
                await stream.WriteAsync(Encoding.ASCII.GetBytes(
                    "HTTP/1.1 200 OK\r\nContent-Length: 8\r\nConnection: close\r\n\r\nsource10"));
            });
            using var handler = new SocketsHttpHandler { UseProxy = false };
            using var client = new HttpClient(handler) { Timeout = TimeSpan.FromSeconds(15) };
            Check(await client.GetStringAsync("http://127.0.0.1:" + port + "/") == "source10",
                "HTTP client, sockets and async loopback server");
            await server;
        }
        finally { listener.Stop(); }
        GC.Collect(2, GCCollectionMode.Forced, true, true);
        string runtimeDirectory = Path.GetDirectoryName(typeof(object).Assembly.Location)!;
        string applicationDirectory = AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
        Check(AppDomain.CurrentDomain.GetAssemblies().Where(a => !a.IsDynamic)
            .All(a => Path.GetDirectoryName(a.Location) == runtimeDirectory ||
                Path.GetDirectoryName(a.Location) == applicationDirectory),
            "all loaded managed implementations come from the isolated source10 layout");
    }
}
