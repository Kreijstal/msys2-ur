using System;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Dapplo.HttpExtensions;
using Dapplo.HttpExtensions.JsonNet;
public class Model {public int Count {get;set;}public string Name {get;set;}}
class Handler:HttpMessageHandler {protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken cancellation){if(request.Method!=HttpMethod.Get||request.RequestUri.AbsolutePath!="/capture")throw new Exception("HTTP request routing");return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK){RequestMessage=request,Content=new StringContent("{\"Count\":42,\"Name\":\"λ 🐾\"}",Encoding.UTF8,"application/json")});}}
class Check {static async Task Main(){var serializer=new JsonNetJsonSerializer();var source=new Model{Count=42,Name="λ 🐾"};var copy=(Model)serializer.Deserialize(typeof(Model),serializer.Serialize(source));if(copy.Count!=42||copy.Name!=source.Name)throw new Exception("JSON adapter round trip");JsonNetJsonSerializer.RegisterGlobally();using var client=new HttpClient(new Handler());var response=await client.GetAsAsync<Model>(new Uri("https://example.invalid/capture"));if(response.Count!=42||response.Name!=source.Name)throw new Exception("HTTP-to-JSON conversion");var query=new Uri("https://example.invalid/?label=%CE%BB&n=42").QueryToDictionary();if(query["label"]!="λ"||query["n"]!="42")throw new Exception("query decoding");Console.WriteLine("PASS Dapplo HTTP original request/response conversion, Json.NET adapter, Unicode and URI query parsing");}}
