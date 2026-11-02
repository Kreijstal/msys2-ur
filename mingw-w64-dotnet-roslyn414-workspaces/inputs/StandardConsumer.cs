using System;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp.Formatting;
using Microsoft.CodeAnalysis.Host.Mef;

public static class StandardWorkspaceConsumer
{
    public static string Run()
    {
        var host=MefHostServices.Create(new[]{typeof(Workspace).Assembly,typeof(CSharpFormattingOptions).Assembly});
        using(var workspace=new AdhocWorkspace(host))
        {
            var project=workspace.AddProject("Standard compile boundary",LanguageNames.CSharp);
            if(project.Language!=LanguageNames.CSharp)throw new Exception("Source Standard2.0 Workspaces contract failed");
            return "PASS separately compiled original Standard2.0 workspace/MEF contract consumer";
        }
    }
}
