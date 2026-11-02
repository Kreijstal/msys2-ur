using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using Microsoft.Build.Framework;
using Microsoft.Build.Utilities;

public static class UtilitiesBridge
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    public static string Run()
    {
        Require(typeof(TaskItem).Assembly.GetName().Version.ToString()=="15.1.0.0","Original Utilities identity");
        var item=new TaskItem("owned%3bfile.cs");Require(item.ItemSpec=="owned;file.cs" && ((ITaskItem2)item).EvaluatedIncludeEscaped=="owned%3bfile.cs","Item escaping contract");
        item.SetMetadata("Owned","value%3b✓");Require(item.GetMetadata("owned")=="value;✓","Case-insensitive metadata and unescaping");
        ((ITaskItem2)item).SetMetadataValueLiteral("Literal","one;two%");Require(item.GetMetadata("literal")=="one;two%" && ((ITaskItem2)item).GetMetadataValueEscaped("Literal").Contains("%3b"),"Literal metadata escaping");
        var clone=new TaskItem(item);clone.SetMetadata("Owned","clone");Require(item.GetMetadata("Owned")=="value;✓" && clone.GetMetadata("Owned")=="clone","Metadata clone isolation");
        var destination=new TaskItem("destination");destination.SetMetadata("Owned","existing");item.CopyMetadataTo(destination);Require(destination.GetMetadata("Owned")=="existing" && destination.GetMetadata("Literal")=="one;two%","Metadata copy preserves destination");
        Require(Path.IsPathRooted(item.GetMetadata("FullPath")) && item.GetMetadata("Extension")==".cs","Built-in file metadata");
        bool invalid=false;try{item.SetMetadata("FullPath","invalid");}catch(ArgumentException){invalid=true;}Require(invalid,"Reserved metadata negative control");
        var line=new CommandLineBuilder();line.AppendSwitchIfNotNull("/out:","owned path/output.dll");line.AppendFileNameIfNotNull("input file.cs");Require(line.ToString()=="/out:\"owned path/output.dll\" \"input file.cs\"","Command line quoting");
        invalid=false;try{line.AppendFileNameIfNotNull("bad\"name.cs");}catch(ArgumentException){invalid=true;}Require(invalid,"Embedded quote negative control");
        var engine=new Engine();var task=new OwnedTask();task.BuildEngine=engine;Require(task.Execute(),"Custom task execution");
        Require(engine.Messages.Count==1 && engine.Messages[0].Message=="Owned ✓ 42","Typed task message delivery");
        task.Log.LogWarning("Owned warning {0}",7);task.Log.LogError("Owned error {0}",9);Require(task.Log.HasLoggedErrors && engine.Warnings.Count==1 && engine.Errors.Count==1,"Warning/error delivery and error state");
        var good=new OwnedTool(0);good.BuildEngine=new Engine();Require(good.Execute() && good.ExitCode==0,"Original ToolTask native child success");
        var badEngine=new Engine();var bad=new OwnedTool(7);bad.BuildEngine=badEngine;Require(!bad.Execute() && bad.ExitCode==7 && badEngine.Errors.Count!=0,"Original ToolTask native child failure");
        return "PASS original Utilities16 TaskItem escaping/metadata/cloning, command lines, task logging and ToolTask native child success/failure";
    }
    sealed class OwnedTask:Microsoft.Build.Utilities.Task
    {
        public override bool Execute(){Log.LogMessage(MessageImportance.High,"Owned ✓ {0}",42);return !Log.HasLoggedErrors;}
    }
    sealed class OwnedTool:ToolTask
    {
        readonly int code;public OwnedTool(int code){this.code=code;}
        protected override string ToolName{get{return "cmd.exe";}}
        protected override string GenerateFullPathToTool(){return Environment.GetEnvironmentVariable("ComSpec");}
        protected override string GenerateCommandLineCommands(){return "/d /c exit "+code;}
    }
    sealed class Engine:IBuildEngine
    {
        public readonly List<BuildMessageEventArgs> Messages=new List<BuildMessageEventArgs>();
        public readonly List<BuildWarningEventArgs> Warnings=new List<BuildWarningEventArgs>();
        public readonly List<BuildErrorEventArgs> Errors=new List<BuildErrorEventArgs>();
        public bool ContinueOnError{get{return false;}}public int LineNumberOfTaskNode{get{return 1;}}public int ColumnNumberOfTaskNode{get{return 1;}}public string ProjectFileOfTaskNode{get{return "owned.proj";}}
        public void LogErrorEvent(BuildErrorEventArgs e){Errors.Add(e);}public void LogWarningEvent(BuildWarningEventArgs e){Warnings.Add(e);}public void LogMessageEvent(BuildMessageEventArgs e){Messages.Add(e);}public void LogCustomEvent(CustomBuildEventArgs e){}
        public bool BuildProjectFile(string project,string[] targets,IDictionary properties,IDictionary outputs){throw new NotSupportedException();}
    }
}
