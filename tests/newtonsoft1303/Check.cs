using System;
using System.Linq;
using System.Dynamic;
using System.Xml.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
public class Model {public string Name {get;set;}public int[] Values {get;set;}}
class Check {static void Main(){var value=new Model{Name="λ 🐾",Values=new[]{1,2,3}};var text=JsonConvert.SerializeObject(value);var copy=JsonConvert.DeserializeObject<Model>(text);if(copy.Name!=value.Name||!copy.Values.SequenceEqual(value.Values))throw new Exception("JSON model round trip");var token=JObject.Parse(text);if((int)token.SelectToken("Values[2]")!=3)throw new Exception("JSON path");dynamic obj=JObject.Parse("{\"Answer\":42}");if((int)obj.Answer!=42)throw new Exception("dynamic binding");var xml=JsonConvert.DeserializeXNode("{\"root\":{\"value\":\"λ\"}}");if(xml.Root.Element("value").Value!="λ")throw new Exception("XML conversion");var name=typeof(JsonConvert).Assembly.GetName();if(name.Version!=new Version(13,0,0,0)||Convert.ToHexString(name.GetPublicKeyToken()).ToLowerInvariant()!="30ad4fe6b2a6aeed")throw new Exception("original assembly identity");Console.WriteLine("PASS Newtonsoft.Json typed/Unicode/dynamic/JSON-path/XML and original strong identity");}}
