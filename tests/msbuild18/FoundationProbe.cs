using System;
using System.Collections;
using System.Linq;
using System.Reflection;
using System.Runtime.Versioning;
using System.Threading.Tasks;
using Microsoft.Build.Framework;
using Microsoft.NET.StringTools;

internal static class FoundationProbe
{
    static void Require(bool value, string message) { if (!value) throw new Exception(message); }
    static int Main()
    {
        Require(Environment.Version.Major == 10, "Source NET10 runtime");
        foreach (var assembly in new[] { typeof(Strings).Assembly, typeof(IBuildEngine).Assembly })
        {
            Require(assembly.GetCustomAttribute<TargetFrameworkAttribute>()?.FrameworkName == ".NETCoreApp,Version=v10.0", "Original NET10 target");
            Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant() == "b03f5f7f11d50a3a", "Original Microsoft signing identity");
            Require(System.IO.Path.GetDirectoryName(assembly.Location) == AppContext.BaseDirectory.TrimEnd(System.IO.Path.DirectorySeparatorChar), "Only this source build's library bytes");
        }
        Require(typeof(Strings).Assembly.GetName().Version == new Version(1,0,0,0), "StringTools assembly version");
        Require(typeof(IBuildEngine).Assembly.GetName().Version == new Version(15,1,0,0), "Framework assembly version");
        string text = new string("  λ/source/世界  ".ToCharArray());
        string interned = Strings.WeakIntern(text);
        Require(ReferenceEquals(interned, Strings.WeakIntern(new string(text.ToCharArray()))), "Weak interning identity");
        Require(ReferenceEquals(interned, Strings.WeakIntern(text.AsSpan())), "Span and string interning share pool");
        using (var builder = Strings.GetSpanBasedStringBuilder())
        {
            builder.Append("  λ/"); builder.Append("source".AsMemory()); builder.Append("/世界  "); builder.Trim();
            Require(builder.ToString() == "λ/source/世界" && builder.Length == "λ/source/世界".Length, "Segmented Unicode append/trim");
            Require(builder[0] == 'λ' && builder.Equals("λ/source/世界"), "Index/equality");
        }
        using (var recycled = Strings.GetSpanBasedStringBuilder()) Require(recycled.Length == 0, "Disposed builder recycled empty");
        Strings.EnableDiagnostics();
        var values = Enumerable.Range(0,128).Select(i => Strings.WeakIntern("source-key-"+i)).ToArray();
        Parallel.For(0,20000,i => Require(ReferenceEquals(values[i%128],Strings.WeakIntern(new string(values[i%128].ToCharArray()))), "Concurrent interning"));
        Require(Strings.CreateDiagnosticReport().Length > 0, "Interner diagnostic report");
        GC.KeepAlive(values); GC.KeepAlive(interned);
        Console.WriteLine("PASS source NET10 StringTools:Unicode spans/builders,recycling,interning and 20000 concurrent lookups");
        var context = new BuildEventContext(1,2,3,4);
        Require(context == new BuildEventContext(1,2,3,4) && context != new BuildEventContext(1,2,3,5), "Event context equality");
        var message = new BuildMessageEventArgs("source λ", "help", "fixture", MessageImportance.High) { BuildEventContext = context };
        Require(message.Message == "source λ" && message.Importance == MessageImportance.High && message.BuildEventContext.TaskId == 4, "Event payload/context");
        var engine = new ProbeEngine();
        ITask task = new ProbeTask { BuildEngine = engine };
        Require(task.Execute() && engine.Messages == 1 && engine.Last == "task λ", "Real task/build-engine interface callback");
        Console.WriteLine("PASS source NET10 MSBuild.Framework:task interfaces,Unicode build events,event contexts and signing/target identities");
        return 0;
    }
    sealed class ProbeTask : ITask
    {
        public IBuildEngine BuildEngine { get; set; } = null!;
        public ITaskHost HostObject { get; set; } = null!;
        public bool Execute() { BuildEngine.LogMessageEvent(new BuildMessageEventArgs("task λ",null!,"fixture",MessageImportance.High)); return true; }
    }
    sealed class ProbeEngine : IBuildEngine
    {
        public int Messages; public string? Last;
        public bool ContinueOnError => false;
        public int LineNumberOfTaskNode => 1;
        public int ColumnNumberOfTaskNode => 1;
        public string ProjectFileOfTaskNode => "source.proj";
        public void LogErrorEvent(BuildErrorEventArgs e) => throw new Exception(e.Message);
        public void LogWarningEvent(BuildWarningEventArgs e) { }
        public void LogCustomEvent(CustomBuildEventArgs e) { }
        public void LogMessageEvent(BuildMessageEventArgs e) { Messages++; Last=e.Message; }
        public bool BuildProjectFile(string file,string[] targets,IDictionary globals,IDictionary outputs) => throw new NotSupportedException();
    }
}
