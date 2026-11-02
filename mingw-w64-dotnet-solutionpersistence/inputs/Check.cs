using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Versioning;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.VisualStudio.SolutionPersistence;
using Microsoft.VisualStudio.SolutionPersistence.Model;
using Microsoft.VisualStudio.SolutionPersistence.Serializer;

internal static class Check
{
    internal static void Require(bool value,string message) { if (!value) throw new Exception(message); }
    static string Snapshot(SolutionModel model) => string.Join("\n",model.SolutionProjects.Select(p => p.Id+"|"+p.FilePath.Replace('\\','/')).OrderBy(s=>s));
    static async Task Main(string[] args)
    {
        var assembly=typeof(SolutionModel).Assembly;
        Require(assembly.GetCustomAttribute<TargetFrameworkAttribute>()?.FrameworkName==".NETCoreApp,Version=v8.0","Original NET8 target");
        Require(assembly.GetName().Version==new Version(1,0,52,0),"SourceBuild SDK assembly version");
        Require(Path.GetDirectoryName(assembly.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"Consumer-local source library");
        var refs=Directory.GetFiles(args[0],"*.dll").Select(p=>MetadataReference.CreateFromFile(p));
        CheckApi.Run(refs,assembly.Location,args[1]);
        Require(SolutionSerializers.GetSerializerByMoniker("source.sln")==SolutionSerializers.SlnFileV12 && SolutionSerializers.GetSerializerByMoniker("source.slnx")==SolutionSerializers.SlnXml,"Moniker selection");
        var source=new SolutionModel();var folder=source.AddFolder("/λ-folder/");
        source.AddProject("λ-folder/世界.csproj",projectTypeName:null,folder:folder);
        source.AddProject("other.vbproj",projectTypeName:null);
        foreach(var serializer in SolutionSerializers.Serializers)
        {
            string path=Path.Combine(args[2],"owned λ"+(serializer==SolutionSerializers.SlnXml?".slnx":".sln"));
            await serializer.SaveAsync(path,source,CancellationToken.None);
            var loaded=await serializer.OpenAsync(path,CancellationToken.None);
            Require(Snapshot(loaded)==Snapshot(source),"Owned Unicode model roundtrip: "+serializer.Name);
        }
        int vectors=0;
        foreach(string file in new[]{"Traditional.slnx.xml","Everything.slnx.xml","Min.sln.txt","Giant.sln.txt","OrchardCore.sln.txt"})
        {
            string path=Path.Combine(args[3],file);Require(File.Exists(path),"Original test vector missing: "+file);
            ISolutionSerializer serializer=file.EndsWith(".xml")?SolutionSerializers.SlnXml:SolutionSerializers.SlnFileV12;
            SolutionModel model;
            await using(var stream=File.OpenRead(path))model=file.EndsWith(".xml")?await SolutionSerializers.SlnXml.OpenAsync(stream,CancellationToken.None):await SolutionSerializers.SlnFileV12.OpenAsync(stream,CancellationToken.None);
            string output=Path.Combine(args[2],"vector-"+(vectors++)+(file.EndsWith(".xml")?".slnx":".sln"));
            await serializer.SaveAsync(output,model,CancellationToken.None);
            Require(Snapshot(await serializer.OpenAsync(output,CancellationToken.None))==Snapshot(model),"Original vector model changed: "+file);
        }
        var bad=Path.Combine(args[2],"bad.slnx");await File.WriteAllTextAsync(bad,"<WrongRoot/>");bool rejected=false;
        try { await SolutionSerializers.SlnXml.OpenAsync(bad,CancellationToken.None); } catch(Exception e) when(e is not OperationCanceledException) { rejected=true; }
        Require(rejected,"Invalid XML solution rejected");
        using var canceled=new CancellationTokenSource();canceled.Cancel();bool canceledRead=false;
        try { await SolutionSerializers.SlnFileV12.OpenAsync(Path.Combine(args[2],"owned λ.sln"),canceled.Token); } catch(OperationCanceledException) { canceledRead=true; }
        Require(canceledRead,"Canceled SLN read");
        // The original XML reader is synchronous and does not inspect this token.
        var xmlWithCanceledToken=await SolutionSerializers.SlnXml.OpenAsync(Path.Combine(args[2],"owned λ.slnx"),canceled.Token);
        Require(Snapshot(xmlWithCanceledToken)==Snapshot(source),"Original XML reader with pre-canceled token");
        Console.WriteLine("PASS source SolutionPersistence1.0.52:all original APIs,Unicode SLN/SLNX model roundtrips,"+vectors+" upstream vectors,invalid input and SLN cancellation");
        Console.WriteLine("OBSERVED upstream behavior: XML reading completes with a pre-canceled token; XML cancellation is not supported by this reader");
    }
}
