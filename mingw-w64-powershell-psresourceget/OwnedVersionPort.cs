using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Management.Automation;
using System.Reflection;

[Cmdlet(VerbsDiagnostic.Test,"OwnedPSResourceVersionPort")]
public sealed class OwnedPSResourceVersionPort : PSCmdlet
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    protected override void ProcessRecord()
    {
        var module=AppDomain.CurrentDomain.GetAssemblies().Single(v=>v.GetName().Name=="Microsoft.PowerShell.PSResourceGet");
        var repository=module.GetType("Microsoft.PowerShell.PSResourceGet.UtilClasses.PSRepositoryInfo");
        var api=repository.GetNestedType("APIVersion");
        object repo=Activator.CreateInstance(repository,new object[]{"OwnedVersionFixture",new Uri("https://127.0.0.1/owned"),50,true,null,Enum.Parse(api,"ContainerRegistry"),true});
        var serverType=module.GetType("Microsoft.PowerShell.PSResourceGet.ContainerRegistryServerAPICalls");
        object server=Activator.CreateInstance(serverType,BindingFlags.Public|BindingFlags.Instance,null,new object[]{repo,this,null,"owned-source-fixture"},null);
        try
        {
            var method=serverType.GetMethod("GetPackagesWithRequiredVersion",BindingFlags.Instance|BindingFlags.NonPublic);var parameters=method.GetParameters();
            Type listType=parameters[0].ParameterType,tokenType=listType.GenericTypeArguments[0],valueType=tokenType.Assembly.GetType("Newtonsoft.Json.Linq.JValue");
            object MakeList(string[] values){var list=(IList)Activator.CreateInstance(listType);foreach(var value in values)list.Add(Activator.CreateInstance(valueType,new object[]{value}));return list;}
            object Parse(Type type,string text)=>type.GetMethod("Parse",new[]{typeof(string)}).Invoke(null,new object[]{text});
            string[] Evaluate(string[] tags,string kind,string range,string exact,bool prerelease,bool expectError=false)
            {
                object[] args={MakeList(tags),Enum.Parse(parameters[1].ParameterType,kind),Parse(parameters[2].ParameterType,range),exact==null?null:Parse(parameters[3].ParameterType,exact),"OwnedPackage",prerelease,null};
                object result=method.Invoke(server,args);
                if(expectError){Require(result==null && args[6] is ErrorRecord,"original invalid-version error");return Array.Empty<string>();}
                Require(args[6]==null && result!=null,"original version helper succeeds");
                Require(result.GetType().GenericTypeArguments[0].FullName=="NuGet.Versioning.SemanticVersion","qualified source NuGet key type");
                var values=new List<string>();foreach(var entry in (IEnumerable)result)values.Add((string)entry.GetType().GetProperty("Value").GetValue(entry));return values.ToArray();
            }
            var tags=new[]{"2.0.0","1.10.0","1.3.0-preview","1.2.0"};
            Require(Evaluate(tags,"VersionRange","[1.0.0,2.0.0)",null,false).SequenceEqual(new[]{"1.2.0","1.10.0"}),"numeric source NuGet ordering and stable range filter");
            Require(Evaluate(tags,"VersionRange","[1.0.0,2.0.0)",null,true).SequenceEqual(new[]{"1.2.0","1.3.0-preview","1.10.0"}),"original prerelease inclusion/order");
            Require(Evaluate(tags,"SpecificVersion","0.0.0","1.2",false).SequenceEqual(new[]{"1.2.0"}),"original normalized exact-version match");
            Evaluate(new[]{"invalid-version"},"VersionRange","0.0.0",null,false,true);
            WriteObject("PASS original ACR version-selection helper in an active source cmdlet: qualified NuGet key, numeric ordering, stable/prerelease ranges, normalized exact match and invalid-version error");
        }
        finally
        {
            foreach(Type type in new[]{serverType,serverType.BaseType})
                (type.GetField("_sessionClient",BindingFlags.Instance|BindingFlags.NonPublic)?.GetValue(server) as IDisposable)?.Dispose();
        }
    }
}
