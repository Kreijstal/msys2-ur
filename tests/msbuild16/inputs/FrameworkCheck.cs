using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Serialization;
using System.Text.Json;
using Microsoft.Build.Framework;

static class Program
{
    static void Require(bool value,string message) { if(!value)throw new Exception(message); }
    static void Main(string[] args)
    {
        var assembly=typeof(BuildEventContext).Assembly;
        Require(assembly.GetName().Version==new Version(15,1,0,0),"Original assembly version");
        Require(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>()!.Version=="16.0.461.62831" && assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()!.InformationalVersion=="16.0.461+g6ff56ef63c","Original release metadata versions");
        Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="b03f5f7f11d50a3a","Original public signing identity");
        Require(assembly.GetCustomAttribute<System.Runtime.Versioning.TargetFrameworkAttribute>()!.FrameworkName==".NETStandard,Version=v2.0","Original NS2 profile");
        Require(Path.GetDirectoryName(assembly.Location)==Path.TrimEndingDirectorySeparator(AppContext.BaseDirectory),"Must load candidate from consumer output");
        using var baseline=JsonDocument.Parse(File.ReadAllText(args[0]));
        var expected=baseline.RootElement.GetProperty("api").EnumerateArray().Select(v=>v.GetString()!).ToArray();
        var actual=Api.Read(assembly.Location);
        Require(expected.SequenceEqual(actual),"Original 743-entry API metadata inventory");
        using(var definition=Mono.Cecil.AssemblyDefinition.ReadAssembly(assembly.Location))
            Require(definition.MainModule.AssemblyReferences.Select(a=>a.FullName).SequenceEqual(baseline.RootElement.GetProperty("references").EnumerateArray().Select(v=>v.GetString()!)),"Original runtime dependency table");
        var context=new BuildEventContext(1,2,3,4,5,6,7);
        Require(context.SubmissionId==1 && context.NodeId==2 && context.EvaluationId==3 && context.ProjectInstanceId==4 && context.ProjectContextId==5 && context.TargetId==6 && context.TaskId==7,"Context identities");
        var equal=new BuildEventContext(1,2,3,4,5,6,7);
        Require(context.Equals(equal) && context.GetHashCode()==equal.GetHashCode(),"Context equality/hash");
        Require(!context.Equals(new BuildEventContext(1,2,3,4,5,6,8)),"Context negative control");
        var serializer=new DataContractSerializer(typeof(BuildEventContext));
        using var stream=new MemoryStream();serializer.WriteObject(stream,context);stream.Position=0;
        var restored=(BuildEventContext)serializer.ReadObject(stream)!;
        Require(context.Equals(restored),"Serializable context private-field round trip");
        var message=new BuildMessageEventArgs("Owned {0}: {1}","help","sender",MessageImportance.High,DateTime.UtcNow,"Unicode","✓");
        message.BuildEventContext=context;
        Require(message.Message=="Owned Unicode: ✓" && message.Importance==MessageImportance.High && message.HelpKeyword=="help" && message.SenderName=="sender" && message.BuildEventContext.Equals(context),"Message formatting/context");
        Require(typeof(ITask).IsInterface && typeof(ITaskItem2).GetInterfaces().Contains(typeof(ITaskItem)),"Task interfaces");
        Require(typeof(TaskShape).GetProperty(nameof(TaskShape.Input))!.GetCustomAttribute<RequiredAttribute>()!=null && typeof(TaskShape).GetProperty(nameof(TaskShape.Result))!.GetCustomAttribute<OutputAttribute>()!=null,"Task parameter attributes");
        Console.WriteLine("PASS original NS2 identity, all 743 published API entries and identical netstandard-only runtime dependency table");
        Console.WriteLine("PASS task contracts, Unicode lazy message formatting, context equality/negative control and DataContract serialization");
    }
    sealed class TaskShape
    {
        [Required] public string Input {get;set;}="owned";
        [Output] public string Result {get;set;}="result";
    }
}
