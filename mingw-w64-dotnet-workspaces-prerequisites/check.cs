using System;
using System.Buffers;
using System.Collections.Generic;
using System.Composition;
using System.Composition.Convention;
using System.Composition.Hosting;
using System.IO;
using System.IO.Pipelines;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

public interface IPlugin { string Name { get; } }
[Export(typeof(IPlugin)), ExportMetadata("Name","alpha"), Shared]
public sealed class Plugin : IPlugin, IDisposable
{
 public string Name=>"alpha";
 public static int Disposals;
 public void Dispose()=>Interlocked.Increment(ref Disposals);
}
[Export]
public sealed class Consumer
{
 public IPlugin Plugin { get; }
 public bool Ready { get; private set; }
 [ImportingConstructor] public Consumer(IPlugin plugin){Plugin=plugin;}
 [OnImportsSatisfied] public void Finish()=>Ready=true;
}
[Export, Shared("scope")]
public sealed class ScopedPart : IDisposable
{
 public static int Disposals;
 public void Dispose()=>Interlocked.Increment(ref Disposals);
}
[Export]
public sealed class FactoryHolder
{
 [Import, SharingBoundary("scope")] public ExportFactory<ScopedPart> Factory { get; set; }
}
public interface IExternal { int Value { get; } }
public sealed class External : IExternal { public int Value=>37; }
public sealed class ImportTarget { [Import("named")] public IExternal External { get; set; } }
public interface IConvention { string Value { get; } }
public sealed class ConventionPlugin : IConvention { public string Value=>"convention"; }
[Export(typeof(IPlugin))]
public sealed class DuplicatePlugin : IPlugin { public string Name=>"duplicate"; }
[Export]
public sealed class MissingImport { [Import] public IExternal External { get; set; } }
class Program
{
 static void Require(bool value,string message){if(!value)throw new Exception(message);}
 static void Composition()
 {
  var supplied=new External();
  using(var host=new ContainerConfiguration().WithPart<Plugin>().WithPart<Consumer>().WithPart<ScopedPart>().WithPart<FactoryHolder>().WithExport<IExternal>(supplied,"named").CreateContainer())
  {
   var consumer=host.GetExport<Consumer>();
   Require(consumer.Ready&&consumer.Plugin.Name=="alpha"&&ReferenceEquals(consumer.Plugin,host.GetExport<IPlugin>()),"Constructor injection/shared identity/import completion");
   var metadata=host.GetExport<Lazy<IPlugin,IDictionary<string,object>>>();
   Require((string)metadata.Metadata["Name"]=="alpha"&&ReferenceEquals(metadata.Value,consumer.Plugin),"Lazy metadata import/shared identity");
   var target=new ImportTarget();host.SatisfyImports(target);Require(ReferenceEquals(target.External,supplied)&&target.External.Value==37,"Named instance export/property injection");
   var factory=host.GetExport<FactoryHolder>().Factory;
   using(var first=factory.CreateExport())
   using(var second=factory.CreateExport())Require(!ReferenceEquals(first.Value,second.Value),"Separate sharing-boundary scopes");
   Require(ScopedPart.Disposals==2,"Scoped parts disposed by export lifetime");
   GC.Collect();GC.WaitForPendingFinalizers();
   Require(ReferenceEquals(consumer.Plugin,host.GetExport<IPlugin>()),"Shared identity after compacting collection");
  }
  Require(Plugin.Disposals==1,"Container disposes shared part once");
  var conventions=new ConventionBuilder();conventions.ForType<ConventionPlugin>().Export<IConvention>().Shared();
  using(var host=new ContainerConfiguration().WithPart<ConventionPlugin>(conventions).CreateContainer())
   Require(host.GetExport<IConvention>().Value=="convention"&&ReferenceEquals(host.GetExport<IConvention>(),host.GetExport<IConvention>()),"Convention-based discovery/shared policy");
  using(var host=new ContainerConfiguration().WithPart<MissingImport>().CreateContainer())
  {try{host.GetExport<MissingImport>();throw new Exception("Missing import accepted");}catch(CompositionFailedException){}}
  using(var host=new ContainerConfiguration().WithPart<Plugin>().WithPart<DuplicatePlugin>().CreateContainer())
  {try{host.GetExport<IPlugin>();throw new Exception("Ambiguous contract accepted");}catch(CompositionFailedException){}}
  Console.WriteLine("PASS MEF2 constructor/property/named imports, shared parts, lazy metadata, import completion, instance exports, convention discovery, owned scopes/disposal and missing/ambiguous contracts");
 }
 static async Task Pipelines()
 {
  var pipe=new Pipe(new PipeOptions(pauseWriterThreshold:16,resumeWriterThreshold:8,useSynchronizationContext:false));
  byte[] bytes=Encoding.UTF8.GetBytes("owned-π-pipe-contents");
  pipe.Writer.Write(bytes);
  var flush=pipe.Writer.FlushAsync();Require(!flush.IsCompleted,"Backpressure did not suspend producer");
  var read=await pipe.Reader.ReadAsync();Require(read.Buffer.ToArray().SequenceEqual(bytes),"Segmented UTF8 bytes changed");
  pipe.Reader.AdvanceTo(read.Buffer.End);Require(!(await flush).IsCanceled,"Resumed producer cancelled");
  await pipe.Writer.CompleteAsync();read=await pipe.Reader.ReadAsync();Require(read.IsCompleted,"Writer completion not observed");pipe.Reader.AdvanceTo(read.Buffer.End);await pipe.Reader.CompleteAsync();
  pipe=new Pipe();var waiting=pipe.Reader.ReadAsync();pipe.Reader.CancelPendingRead();read=await waiting;Require(read.IsCanceled,"Pending read cancellation");pipe.Reader.AdvanceTo(read.Buffer.End);await pipe.Reader.CompleteAsync();await pipe.Writer.CompleteAsync();
  using(var stream=new MemoryStream(Encoding.UTF8.GetBytes("source stream reader π")))
  {
   var reader=PipeReader.Create(stream,new StreamPipeReaderOptions(leaveOpen:true));using var output=new MemoryStream();
   await reader.CopyToAsync(output);await reader.CompleteAsync();Require(stream.CanRead&&Encoding.UTF8.GetString(output.ToArray())=="source stream reader π","Reader stream bridge/ownership");
  }
  using(var stream=new MemoryStream())
  {
   var writer=PipeWriter.Create(stream,new StreamPipeWriterOptions(leaveOpen:true));await writer.WriteAsync(bytes);await writer.CompleteAsync();Require(stream.CanWrite&&stream.ToArray().SequenceEqual(bytes),"Writer stream bridge/ownership");
  }
  pipe=new Pipe();using(var stream=pipe.Writer.AsStream(leaveOpen:true)){await stream.WriteAsync(bytes);await stream.FlushAsync();}
  read=await pipe.Reader.ReadAsync();Require(read.Buffer.ToArray().SequenceEqual(bytes),"Pipe writer stream adapter");pipe.Reader.AdvanceTo(read.Buffer.End);await pipe.Writer.CompleteAsync();await pipe.Reader.CompleteAsync();
  pipe=new Pipe();await pipe.Writer.CompleteAsync(new IOException("owned pipeline failure"));
  try{await pipe.Reader.ReadAsync();throw new Exception("Producer exception lost");}catch(IOException e){Require(e.Message=="owned pipeline failure","Producer exception identity");}
  await pipe.Reader.CompleteAsync();
  Console.WriteLine("PASS pipelines asynchronous backpressure/resume, UTF8 buffers/advance, completion, read cancellation, stream bridges/ownership and producer exception propagation");
 }
 static async Task Main(string[] args)
 {
  CheckResources.Run(args[0],args[1]);Composition();await Pipelines();
 }
}
