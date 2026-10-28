using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;
using Azure;
using Azure.Core;
using Azure.Core.Pipeline;

class Program
{
    sealed class Options : ClientOptions {}
    static void Require(bool condition,string message){if(!condition)throw new Exception(message);}
    static async Task Main(string[] args)
    {
        using var hashes=JsonDocument.Parse(File.ReadAllBytes(args[0]));
        foreach(var assembly in new[]{typeof(HttpPipeline).Assembly,typeof(BinaryData).Assembly,typeof(JsonSerializer).Assembly,typeof(System.ClientModel.Primitives.ModelReaderWriter).Assembly})
        {
            Require(Path.GetDirectoryName(assembly.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"foreign loaded runtime "+assembly.GetName().Name);
            Require(Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(assembly.Location))).ToLowerInvariant()==hashes.RootElement.GetProperty(assembly.GetName().Name).GetString(),"loaded source hash "+assembly.GetName().Name);
        }
        Require(typeof(HttpPipeline).Assembly.GetName().Version.ToString()=="1.38.0.0","source Core identity");
        Require(!JsonSerializer.IsReflectionEnabledByDefault,"error parser must use original source-generated context");
        using var listener=new TcpListener(IPAddress.Loopback,0);listener.Start();
        int port=((IPEndPoint)listener.LocalEndpoint).Port;
        var requestBody=Encoding.UTF8.GetBytes("owned λ😀 "+new string('a',40000));
        int requests=0;
        using var timeout=new CancellationTokenSource(TimeSpan.FromSeconds(40));
        var server=Task.Run(async()=>
        {
            for(int i=0;i<3;i++)
            {
                using var socket=await listener.AcceptTcpClientAsync(timeout.Token);
                using var stream=socket.GetStream();
                var header=new List<byte>();var one=new byte[1];
                while(true)
                {
                    Require(header.Count<16000,"bounded owned HTTP headers");
                    Require(await stream.ReadAsync(one,timeout.Token)==1,"request header EOF");
                    header.Add(one[0]);
                    if(header.Count>=4 && header.TakeLast(4).SequenceEqual(new byte[]{13,10,13,10}))break;
                }
                string text=Encoding.ASCII.GetString(header.ToArray());
                Require(text.StartsWith("POST /owned?case="),"request method/path");
                var lengthHeader=text.Split("\r\n").Single(v=>v.StartsWith("Content-Length:",StringComparison.OrdinalIgnoreCase));
                int length=int.Parse(lengthHeader.Split(':')[1]);var body=new byte[length];
                await stream.ReadExactlyAsync(body,timeout.Token);
                Require(body.SequenceEqual(requestBody),"native HTTP UTF8 request payload/retry ownership");
                requests++;
                int status=i==0?503:i==1?200:400;
                string payload=i==0?"{\"error\":{\"code\":\"Retry\",\"message\":\"retry\"}}":i==1?"{\"ok\":true}":"{\"error\":{\"code\":\"OwnedBadRequest\",\"message\":\"owned λ😀\"}}";
                byte[] bytes=Encoding.UTF8.GetBytes(payload);
                var response=Encoding.ASCII.GetBytes("HTTP/1.1 "+status+" Owned\r\nContent-Type: application/json\r\nContent-Length: "+bytes.Length+"\r\nRetry-After: 0\r\nx-ms-request-id: owned-request\r\nConnection: close\r\n\r\n");
                await stream.WriteAsync(response,timeout.Token);await stream.WriteAsync(bytes,timeout.Token);
            }
        },timeout.Token);
        using var handler=new HttpClientHandler{UseProxy=false};using var client=new HttpClient(handler);
        var options=new Options{Transport=new HttpClientTransport(client)};
        options.Retry.MaxRetries=1;options.Retry.Mode=RetryMode.Fixed;options.Retry.Delay=TimeSpan.Zero;options.Retry.MaxDelay=TimeSpan.Zero;
        options.Diagnostics.IsLoggingEnabled=false;options.Diagnostics.IsTelemetryEnabled=false;
        var pipeline=HttpPipelineBuilder.Build(options);
        using(var message=pipeline.CreateMessage())
        {
            message.Request.Method=RequestMethod.Post;
            message.Request.Uri.Reset(new Uri("http://127.0.0.1:"+port+"/owned?case=retry"));
            message.Request.Content=RequestContent.Create(BinaryData.FromBytes(requestBody));
            await pipeline.SendAsync(message,timeout.Token);
            Require(message.Response.Status==200,"source retry policy recovers from503");
            Require(BinaryData.FromStream(message.Response.ContentStream).ToString()=="{\"ok\":true}","HTTP response body");
        }
        using(var message=pipeline.CreateMessage())
        {
            message.Request.Method=RequestMethod.Post;
            message.Request.Uri.Reset(new Uri("http://127.0.0.1:"+port+"/owned?case=error"));
            message.Request.Content=RequestContent.Create(BinaryData.FromBytes(requestBody));
            pipeline.Send(message,timeout.Token);
            var error=new RequestFailedException(message.Response);
            Require(error.Status==400 && error.ErrorCode=="OwnedBadRequest" && error.Message.Contains("owned λ😀"),"original generated JSON error parsing");
        }
        await server;Require(requests==3,"exactly one retry and no400 retry");
        using var cancelled=new CancellationTokenSource();cancelled.Cancel();
        using(var message=pipeline.CreateMessage())
        {
            message.Request.Method=RequestMethod.Get;message.Request.Uri.Reset(new Uri("http://127.0.0.1:"+port+"/owned?case=cancel"));
            bool failed=false;try{await pipeline.SendAsync(message,cancelled.Token);}catch(OperationCanceledException){failed=true;}
            Require(failed,"source HTTP cancellation");
        }
        Console.WriteLine("PASS original source Azure.Core real sync/async HTTP pipeline, UTF8 request/retry ownership,503retry/400negative parsing with reflection disabled, response bodies and cancellation");
    }
}
