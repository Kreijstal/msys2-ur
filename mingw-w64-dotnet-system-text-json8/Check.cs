using System;
using System.Buffers;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;

class Program
{
    static void Require(bool value,string message) { if(!value)throw new Exception(message); }
    public sealed class Model
    {
        public required string Name {get;set;}
        public List<int> Values {get;set;}=new();
        [JsonExtensionData] public Dictionary<string,JsonElement> Extra {get;set;}=new();
    }
    [JsonPolymorphic(TypeDiscriminatorPropertyName="kind")]
    [JsonDerivedType(typeof(Child),"child")]
    public class Base {public string Name {get;set;}="";}
    public sealed class Child : Base {public int Count {get;set;}}
    sealed class Segment : ReadOnlySequenceSegment<byte>
    {
        public Segment(ReadOnlyMemory<byte> bytes) {Memory=bytes;}
        public Segment Append(ReadOnlyMemory<byte> bytes)
        {
            var next=new Segment(bytes) {RunningIndex=RunningIndex+Memory.Length};Next=next;return next;
        }
    }
    static void ReaderChecks()
    {
        byte[] bytes=Encoding.UTF8.GetBytes("{\"name\":\"λ😀\",\"value\":9223372036854775807}");
        var first=new Segment(bytes.AsMemory(0,11));var last=first.Append(bytes.AsMemory(11,3)).Append(bytes.AsMemory(14));
        var reader=new Utf8JsonReader(new ReadOnlySequence<byte>(first,0,last,last.Memory.Length));
        var values=new List<string>();
        while(reader.Read())
        {
            if(reader.TokenType==JsonTokenType.String)values.Add(reader.GetString());
            if(reader.TokenType==JsonTokenType.Number)Require(reader.GetInt64()==long.MaxValue,"segmented Int64 boundary");
        }
        Require(values.SequenceEqual(new[] {"λ😀"}),"segmented UTF8 decoder");
        bool invalid=false;try {using var bad=JsonDocument.Parse("{\"x\":[1,]}");}catch(JsonException){invalid=true;}
        Require(invalid,"malformed JSON rejected");
        bool deep=false;try {using var bad=JsonDocument.Parse("[[[0]]]",new JsonDocumentOptions{MaxDepth=2});}catch(JsonException){deep=true;}
        Require(deep,"maximum-depth enforcement");
    }
    static async Task RuntimeChecks()
    {
        var model=JsonSerializer.Deserialize<Model>("{\"Name\":\"λ😀\",\"Values\":[1,2,3],\"owned\":true}");
        Require(model.Name=="λ😀" && model.Values.Sum()==6 && model.Extra["owned"].GetBoolean(),"reflection/required/extension metadata");
        string serialized=JsonSerializer.Serialize(model);
        Require(JsonSerializer.Deserialize<Model>(serialized).Name==model.Name,"Unicode round trip");
        Base child=new Child{Name="owned",Count=7};
        Require(JsonSerializer.Deserialize<Base>(JsonSerializer.Serialize(child)) is Child {Count:7},"polymorphic metadata");
        JsonElement kept;
        using(var doc=JsonDocument.Parse(serialized))kept=doc.RootElement.Clone();
        Require(kept.GetProperty("Name").GetString()=="λ😀","DOM clone lifetime");
        var node=JsonNode.Parse(serialized).AsObject();node["Name"]="changed";
        Require(JsonSerializer.Deserialize<Model>(node.ToJsonString()).Name=="changed","mutable DOM");
        using var stream=new MemoryStream();
        await JsonSerializer.SerializeAsync(stream,model);stream.Position=0;
        Require((await JsonSerializer.DeserializeAsync<Model>(stream)).Values.Count==3,"async stream round trip");
        using var arrayStream=new MemoryStream(Encoding.UTF8.GetBytes("[1,2,3]"));int sum=0;
        await foreach(int value in JsonSerializer.DeserializeAsyncEnumerable<int>(arrayStream))sum+=value;
        Require(sum==6,"async enumerable streaming");
        ReaderChecks();
        using var output=new MemoryStream();
        using(var writer=new Utf8JsonWriter(output)) {writer.WriteStartObject();writer.WriteString("λ","😀");writer.WriteNumber("n",decimal.MaxValue);writer.WriteEndObject();}
        using var written=JsonDocument.Parse(output.ToArray());
        Require(written.RootElement.GetProperty("λ").GetString()=="😀" && written.RootElement.GetProperty("n").GetDecimal()==decimal.MaxValue,"UTF8 writer/decimal boundary");
        Console.WriteLine("PASS source JSON reflection/required/extension/polymorphic metadata, DOM lifetimes/mutation, async streams/enumerables, segmented UTF8, Unicode, numeric boundaries and malformed/depth rejection");
    }
    static void GeneratorChecks(string path,string framework)
    {
        Assembly generator=AssemblyLoadContext.Default.LoadFromAssemblyPath(Path.GetFullPath(path));
        Require(generator.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion.Contains("81cabf2857a01351e5ab578947c7403a5b128ad1"),"source generator revision");
        object instance=Activator.CreateInstance(generator.GetType("System.Text.Json.SourceGeneration.JsonSourceGenerator",true));
        ISourceGenerator source=instance is IIncrementalGenerator incremental?incremental.AsSourceGenerator():(ISourceGenerator)instance;
        var references=Directory.GetFiles(framework,"*.dll").Where(p=>Path.GetFileName(p)!="System.Text.Json.dll")
            .Select(p=>MetadataReference.CreateFromFile(p)).ToList();
        references.Add(MetadataReference.CreateFromFile(typeof(JsonSerializer).Assembly.Location));
        const string code="""
using System;
using System.Text.Json;
using System.Text.Json.Serialization;
public sealed class OwnedModel {public string Name {get;set;}=""; public int[] Values {get;set;}=Array.Empty<int>();}
[JsonSerializable(typeof(OwnedModel))]
public partial class OwnedContext : JsonSerializerContext {}
public static class OwnedRun
{
    public static string Execute()
    {
        if(JsonSerializer.IsReflectionEnabledByDefault)throw new Exception("Reflection fallback enabled");
        var model=new OwnedModel{Name="λ😀",Values=new[]{1,2,3}};
        string text=JsonSerializer.Serialize(model,OwnedContext.Default.OwnedModel);
        var copy=JsonSerializer.Deserialize(text,OwnedContext.Default.OwnedModel);
        if(copy.Name!=model.Name || copy.Values.Length!=3)throw new Exception("Generated round trip");
        return "owned generated λ😀";
    }
}
""";
        var compilation=CSharpCompilation.Create("OwnedGenerated"+Guid.NewGuid().ToString("N"),
            new[]{CSharpSyntaxTree.ParseText(code)},references,new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));
        GeneratorDriver driver=CSharpGeneratorDriver.Create(source);
        driver=driver.RunGeneratorsAndUpdateCompilation(compilation,out var generated,out var diagnostics);
        Require(!diagnostics.Any(d=>d.Severity==DiagnosticSeverity.Error),string.Join("\n",diagnostics));
        Require(driver.GetRunResult().GeneratedTrees.Count()>=5,"actual original generator output");
        using var image=new MemoryStream();var emit=generated.Emit(image);
        Require(emit.Success,string.Join("\n",emit.Diagnostics));
        image.Position=0;Assembly consumer=AssemblyLoadContext.Default.LoadFromStream(image);
        Require((string)consumer.GetType("OwnedRun").GetMethod("Execute").Invoke(null,null)=="owned generated λ😀","executed generated serializer");
        const string bad="""
using System.Text.Json.Serialization;
[JsonSerializable(typeof(string))]
public class BadContext : JsonSerializerContext {}
""";
        var negative=CSharpCompilation.Create("OwnedNegative",new[]{CSharpSyntaxTree.ParseText(bad)},references,
            new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));
        var result=CSharpGeneratorDriver.Create(source).RunGenerators(negative).GetRunResult();
        var diagnostic=result.Diagnostics.Single(d=>d.Id=="SYSLIB1032");
        Require(diagnostic.GetMessage(CultureInfo.GetCultureInfo("de"))!=diagnostic.GetMessage(CultureInfo.GetCultureInfo("en-US")),"localized original diagnostic");
        Console.WriteLine("PASS original generator "+path+": generated compilation/execution with reflection disabled, SYSLIB1032 rejection and German diagnostic satellite");
    }
    static async Task Main(string[] args)
    {
        if(args[0]=="generator")AppContext.SetSwitch("System.Text.Json.JsonSerializer.IsReflectionEnabledByDefault",false);
        Assembly json=typeof(JsonSerializer).Assembly;
        string candidate=Path.Combine(AppContext.BaseDirectory,"System.Text.Json.dll");
        Require(Path.GetFullPath(json.Location)==Path.GetFullPath(candidate),"inbox JSON implementation substituted: "+json.Location);
        Require(json.GetName().Version.ToString()=="8.0.0.0" && json.GetCustomAttribute<AssemblyFileVersionAttribute>().Version=="8.0.1024.46610","published net8 JSON version");
        Require(Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(json.Location))).Equals(args[1],StringComparison.OrdinalIgnoreCase),"tested JSON bytes differ from source build");
        if(args[0]=="runtime")await RuntimeChecks();else GeneratorChecks(args[2],args[3]);
    }
}
