using System;
using System.ClientModel.Primitives;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;

class Program
{
    static void Require(bool value,string message) {if(!value)throw new Exception(message);}
    public sealed class Model : IJsonModel<Model>
    {
        private Model() {}
        public string Name {get;set;}="";
        public static Model Owned(string name)=>new Model{Name=name};
        public string GetFormatFromOptions(ModelReaderWriterOptions options)=>"J";
        public BinaryData Write(ModelReaderWriterOptions options)
        {
            if(options.Format=="X")return BinaryData.FromString("<name>"+Name+"</name>");
            using var stream=new MemoryStream();using(var writer=new Utf8JsonWriter(stream))Write(writer,options);
            return BinaryData.FromBytes(stream.ToArray());
        }
        public Model Create(BinaryData data,ModelReaderWriterOptions options)
        {
            if(options.Format=="X")return Owned(data.ToString().Replace("<name>","").Replace("</name>",""));
            var reader=new Utf8JsonReader(data.ToMemory().Span);reader.Read();return Create(ref reader,options);
        }
        public void Write(Utf8JsonWriter writer,ModelReaderWriterOptions options)
        {writer.WriteStartObject();writer.WriteString("name",Name);writer.WriteEndObject();}
        public Model Create(ref Utf8JsonReader reader,ModelReaderWriterOptions options)
        {using var doc=JsonDocument.ParseValue(ref reader);return Owned(doc.RootElement.GetProperty("name").GetString());}
    }
    [PersistableModelProxy(typeof(Proxy))]
    public abstract class AbstractModel : IPersistableModel<AbstractModel>
    {
        public string Name {get;protected set;}="";
        public abstract BinaryData Write(ModelReaderWriterOptions options);
        public abstract AbstractModel Create(BinaryData data,ModelReaderWriterOptions options);
        public string GetFormatFromOptions(ModelReaderWriterOptions options)=>"J";
    }
    public sealed class Proxy : AbstractModel
    {
        private Proxy() {}
        public override BinaryData Write(ModelReaderWriterOptions options)=>BinaryData.FromString(Name);
        public override AbstractModel Create(BinaryData data,ModelReaderWriterOptions options)=>new Proxy{Name=data.ToString()};
    }
    static void Main(string[] args)
    {
        var assembly=typeof(ModelReaderWriter).Assembly;
        var hashes=JsonSerializer.Deserialize<System.Collections.Generic.Dictionary<string,string>>(File.ReadAllText(args[0]));
        foreach(var dependency in new[]{assembly,typeof(BinaryData).Assembly,typeof(JsonSerializer).Assembly})
        {
            Require(Path.GetDirectoryName(dependency.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"foreign loaded dependency "+dependency.GetName().Name);
            Require(Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(dependency.Location))).ToLowerInvariant()==hashes[dependency.GetName().Name],"source runtime hash "+dependency.GetName().Name);
        }
        Require(assembly.GetName().Version.ToString()=="1.0.0.0" && Path.GetDirectoryName(assembly.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"foreign ClientModel implementation");
        Require(typeof(BinaryData).Assembly.GetName().Version.ToString()=="1.0.2.0","BinaryData identity");
        Require(typeof(JsonSerializer).Assembly.GetCustomAttribute<AssemblyFileVersionAttribute>().Version=="8.0.1024.46610","source JSON identity");
        var model=Model.Owned("owned λ😀");
        var bytes=ModelReaderWriter.Write(model);Require(ModelReaderWriter.Read<Model>(bytes).Name==model.Name,"generic source JSON model round trip/private constructor");
        Require(((Model)ModelReaderWriter.Read(ModelReaderWriter.Write((object)model),typeof(Model))).Name==model.Name,"object/type model round trip");
        Require(ModelReaderWriter.Read<Model>(ModelReaderWriter.Write(model,new ModelReaderWriterOptions("W")),new ModelReaderWriterOptions("W")).Name==model.Name,"wire-format resolution");
        Require(ModelReaderWriter.Read<Model>(ModelReaderWriter.Write(model,ModelReaderWriterOptions.Xml),ModelReaderWriterOptions.Xml).Name==model.Name,"custom non-JSON persistence dispatch");
        Require(((Model)ModelReaderWriter.Read(ModelReaderWriter.Write((object)model,ModelReaderWriterOptions.Xml),typeof(Model),ModelReaderWriterOptions.Xml)).Name==model.Name,"object custom-format dispatch");
        // Cross the original writer's pooled-buffer boundary and force large UTF8 encoding.
        var large=Model.Owned(new string('a',250000)+" λ😀 "+new string('b',250000));
        var retained=ModelReaderWriter.Write(large);
        for(int i=0;i<6;i++)ModelReaderWriter.Write(Model.Owned(new string((char)('c'+i),600000)));
        GC.Collect();GC.WaitForPendingFinalizers();
        Require(ModelReaderWriter.Read<Model>(retained).Name==large.Name,"large pooled-buffer JSON bytes remain independently owned after reuse/GC");
        Require(ModelReaderWriter.Read<AbstractModel>(BinaryData.FromString("proxy λ")).Name=="proxy λ","original proxy attribute activation/private constructor");
        Require(ModelReaderWriterOptions.Json.Format=="J" && ModelReaderWriterOptions.Xml.Format=="X","default format contracts");
        bool unsupported=false;try{ModelReaderWriter.Write(new object());}catch(InvalidOperationException){unsupported=true;}Require(unsupported,"unsupported write type rejected");
        bool invalid=false;try{ModelReaderWriter.Read<Model>(BinaryData.FromString("{"));}catch(JsonException){invalid=true;}Require(invalid,"native source JSON error propagation");
        bool nullData=false;try{ModelReaderWriter.Read<Model>(null);}catch(ArgumentNullException e){nullData=e.ParamName=="data";}Require(nullData,"null data validation");
        Console.WriteLine("PASS original ClientModel generic/object JSON persistence, large pooled-buffer lifetime, private construction/proxy activation, wire/custom format dispatch, Unicode, unsupported/null/malformed errors with source BinaryData/JSON and exact loaded hashes");
    }
}
