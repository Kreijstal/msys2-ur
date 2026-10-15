using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using YamlDotNet.RepresentationModel;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;
public class Texture { public string Name { get; set; } = ""; public int Width { get; set; } public bool GenerateMipmaps { get; set; } public List<string> Tags { get; set; } = new(); public Dictionary<string, double> Params { get; set; } = new(); public Texture? Fallback { get; set; } }
class Check {
static void Main(){
var asm=typeof(Serializer).Assembly.GetName();
var token=Convert.ToHexString(asm.GetPublicKeyToken()!).ToLowerInvariant();
if(asm.Name!="YamlDotNet"||asm.Version!=new Version(16,0,0,0)||token!="ec19458f3c15af5e")throw new Exception("strong-name identity "+asm.FullName);
// Object graph round trip with a naming convention
var tex=new Texture{Name="grass: \"quoted\" #not-a-comment\nsecond line",Width=256,GenerateMipmaps=true,Tags={"terrain","ünïcödé ✓"},Params={["gamma"]=2.2,["scale"]=-0.5},Fallback=new Texture{Name="checker",Width=8}};
var yaml=new SerializerBuilder().WithNamingConvention(UnderscoredNamingConvention.Instance).Build().Serialize(tex);
if(!yaml.Contains("generate_mipmaps: true"))throw new Exception("naming convention not applied:\n"+yaml);
var back=new DeserializerBuilder().WithNamingConvention(UnderscoredNamingConvention.Instance).Build().Deserialize<Texture>(yaml);
if(back.Name!=tex.Name||back.Width!=256||!back.GenerateMipmaps||!back.Tags.SequenceEqual(tex.Tags)||back.Params["gamma"]!=2.2||back.Params["scale"]!=-0.5||back.Fallback?.Name!="checker"||back.Fallback.Width!=8)throw new Exception("round trip mismatch:\n"+yaml);
// Anchors/aliases, merge-free flow collections, multiple documents through the representation model
var stream=new YamlStream();stream.Load(new StringReader("base: &b {w: 4, h: [1, 2, 3]}\ncopy: *b\n---\n- !!int 42\n- 'single'\n- |\n  literal\n  block\n"));
if(stream.Documents.Count!=2)throw new Exception("documents "+stream.Documents.Count);
var map=(YamlMappingNode)stream.Documents[0].RootNode;
if(!ReferenceEquals(map["base"],map["copy"]))throw new Exception("alias did not resolve to anchored node");
if(((YamlSequenceNode)((YamlMappingNode)map["copy"])["h"]).Children.Count!=3)throw new Exception("flow sequence");
var seq=(YamlSequenceNode)stream.Documents[1].RootNode;
if(((YamlScalarNode)seq[0]).Value!="42"||((YamlScalarNode)seq[1]).Value!="single"||((YamlScalarNode)seq[2]).Value!="literal\nblock\n")throw new Exception("scalars");
// Untyped deserialization
var dict=(Dictionary<object,object>)new Deserializer().Deserialize(new StringReader("a: 1\nb: [x, y]\n"))!;
if((string)dict["a"]!="1"||((List<object>)dict["b"]).Count!=2)throw new Exception("untyped deserialize");
Console.WriteLine("PASS YamlDotNet "+asm.Version+" strong-named token "+token+"; typed round trip with underscored naming, anchors/aliases, multi-document stream, literal block, untyped deserialize");}}
