using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Collections.Immutable;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks.Dataflow;
using Microsoft.Build.Framework;
using Microsoft.Build.Tasks;
using Microsoft.Build.Utilities;
using Microsoft.CSharp;

public static class TasksBridge
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static Engine Setup(Microsoft.Build.Utilities.Task task){var engine=new Engine();task.BuildEngine=engine;return engine;}
    public static string Run(string owned)
    {
        string root=Path.Combine(owned,"operations-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);
        try
        {
            string source=Path.Combine(root,"source Ω.txt"),copy=Path.Combine(root,"copied Ω.txt");
            var write=new WriteLinesToFile{File=new TaskItem(source),Lines=new[]{new TaskItem("héllo Ω"),new TaskItem("second")},Overwrite=true,Encoding="UTF-8"};Setup(write);Require(write.Execute(),"WriteLinesToFile");
            var read=new ReadLinesFromFile{File=new TaskItem(source)};Setup(read);Require(read.Execute() && read.Lines.Select(x=>x.ItemSpec).SequenceEqual(new[]{"héllo Ω","second"}),"ReadLinesFromFile Unicode");
            var copying=new Copy{SourceFiles=new[]{new TaskItem(source)},DestinationFiles=new[]{new TaskItem(copy)},SkipUnchangedFiles=true};Setup(copying);Require(copying.Execute() && File.ReadAllBytes(copy).SequenceEqual(File.ReadAllBytes(source)),"Copy exact bytes");
            Require(copying.Execute() && copying.CopiedFiles.Length==1,"Copy unchanged-file path");
            var hash=new GetFileHash{Files=new[]{new TaskItem(source),new TaskItem(copy)},Algorithm="SHA256",HashEncoding="hex"};Setup(hash);Require(hash.Execute(),"GetFileHash");
            string expected;using(var algorithm=SHA256.Create())expected=BitConverter.ToString(algorithm.ComputeHash(File.ReadAllBytes(source))).Replace("-","");
            Require(hash.Items.Length==2 && hash.Items.All(x=>string.Equals(x.GetMetadata("FileHash"),expected,StringComparison.OrdinalIgnoreCase)),"parallel file hash values");
            var verify=new VerifyFileHash{File=copy,Hash=expected,Algorithm="SHA256",HashEncoding="hex"};Setup(verify);Require(verify.Execute(),"VerifyFileHash correct digest");
            var wrong=new VerifyFileHash{File=copy,Hash=new string('0',64),Algorithm="SHA256",HashEncoding="hex"};var wrongEngine=Setup(wrong);Require(!wrong.Execute() && wrongEngine.Errors.Count>0,"VerifyFileHash mismatch negative control");
            var target=new AssignTargetPath{RootFolder=root,Files=new[]{new TaskItem(copy)}};Setup(target);Require(target.Execute() && target.AssignedFiles[0].GetMetadata("TargetPath")==Path.GetFileName(copy),"AssignTargetPath");
            var identity=new GetAssemblyIdentity{AssemblyFiles=new[]{new TaskItem(Path.Combine(owned,"Microsoft.Build.Tasks.Core.dll"))}};Setup(identity);Require(identity.Execute() && identity.Assemblies.Length==1 && identity.Assemblies[0].ItemSpec.Contains("Version=15.1.0.0"),"GetAssemblyIdentity original Tasks");
            using(var pe=new PEReader(File.OpenRead(Path.Combine(owned,"Microsoft.Build.Tasks.Core.dll"))))Require(pe.HasMetadata && pe.GetMetadataReader().IsAssembly,"source Metadata dependency");
            Require(ImmutableArray.Create(20,22).Sum()==42,"source Immutable dependency");
            var reference=new TaskItem("System.CodeDom");reference.SetMetadata("HintPath",Path.Combine(owned,"System.CodeDom.dll"));
            var resolve=new ResolveAssemblyReference{Assemblies=new[]{reference},SearchPaths=new[]{"{HintPathFromItem}"},FindDependencies=false,FindRelatedFiles=false,FindSatellites=false,FindSerializationAssemblies=false,TargetFrameworkVersion="v4.7.2"};Setup(resolve);
            Require(resolve.Execute() && resolve.ResolvedFiles.Length==1 && Path.GetFullPath(resolve.ResolvedFiles[0].ItemSpec)==Path.Combine(owned,"System.CodeDom.dll"),"ResolveAssemblyReference exact source assembly");
            string resx=Path.Combine(root,"strings.resx"),resources=Path.Combine(root,"strings.resources");
            File.WriteAllText(resx,"<root><resheader name=\"resmimetype\"><value>text/microsoft-resx</value></resheader><resheader name=\"version\"><value>2.0</value></resheader><data name=\"Owned\" xml:space=\"preserve\"><value>héllo Ω</value></data></root>");
            var generate=new GenerateResource{Sources=new[]{new TaskItem(resx)},OutputResources=new[]{new TaskItem(resources)},ExecuteAsTool=false,UseSourcePath=true};Setup(generate);Require(generate.Execute(),"GenerateResource string resx");
            using(var reader=new System.Resources.ResourceReader(resources)){var entries=reader.Cast<DictionaryEntry>().ToDictionary(x=>(string)x.Key,x=>(string)x.Value);Require(entries["Owned"]=="héllo Ω","GenerateResource exact string");}
            var good=new Exec{Command="echo source-tasks16-proof",ConsoleToMSBuild=true,WorkingDirectory=root};Setup(good);Require(good.Execute() && good.ConsoleOutput.Any(x=>x.ItemSpec=="source-tasks16-proof"),"Exec native child/output");
            var bad=new Exec{Command="exit 7",WorkingDirectory=root};var badEngine=Setup(bad);Require(!bad.Execute() && bad.ExitCode==7 && badEngine.Errors.Count>0,"Exec failure and error logging");
            Download(root);
            using(var provider=new CSharpCodeProvider())Require(provider.CreateEscapedIdentifier("class")=="@class","source CodeDom dependency");
            var buffer=new BufferBlock<int>();Require(buffer.Post(42) && buffer.Receive()==42,"source Dataflow dependency");buffer.Complete();buffer.Completion.GetAwaiter().GetResult();
            var encoding=System.Text.CodePagesEncodingProvider.Instance.GetEncoding(1252);Require(encoding.GetBytes("€").SequenceEqual(new byte[]{128}),"source CodePages dependency");
            Require(Microsoft.Win32.Registry.CurrentUser.Name=="HKEY_CURRENT_USER","source Registry read-only root");
            Require(typeof(string).GetTypeInfo().DeclaredMethods.Any(m=>m.Name=="StartsWith"),"Standard2 reflection BCL");
            var deletion=new Delete{Files=new[]{new TaskItem(copy)}};Setup(deletion);Require(deletion.Execute() && !File.Exists(copy),"Delete owned file");
            return "PASS original Tasks16 Unicode file IO/copy/delete/hash, negative hash, metadata/RAR, resources, Exec success/failure, local HTTP and exact old dependency execution";
        }
        finally{Directory.Delete(root,true);}
    }
    static void Download(string root)
    {
        byte[] body=Encoding.UTF8.GetBytes("owned HTTP héllo Ω");
        var listener=new TcpListener(IPAddress.Loopback,0);listener.Start();int port=((IPEndPoint)listener.LocalEndpoint).Port;
        var server=System.Threading.Tasks.Task.Run(()=>
        {
            using(var client=listener.AcceptTcpClient())
            using(var stream=client.GetStream())
            {
                stream.ReadTimeout=10000;var request=new StringBuilder();
                while(request.Length<8192 && !request.ToString().EndsWith("\r\n\r\n",StringComparison.Ordinal)){int b=stream.ReadByte();if(b<0)break;request.Append((char)b);}
                Require(request.ToString().StartsWith("GET ",StringComparison.Ordinal),"local HTTP fixture request");
                byte[] header=Encoding.ASCII.GetBytes("HTTP/1.1 200 OK\r\nContent-Length: "+body.Length+"\r\nConnection: close\r\n\r\n");stream.Write(header,0,header.Length);stream.Write(body,0,body.Length);
            }
        });
        try
        {
            var download=new DownloadFile{SourceUrl="http://127.0.0.1:"+port+"/payload.txt",DestinationFolder=new TaskItem(root),DestinationFileName=new TaskItem("download.txt"),SkipUnchangedFiles=false,Retries=0};Setup(download);
            Require(download.Execute() && File.ReadAllBytes(download.DownloadedFile.ItemSpec).SequenceEqual(body),"DownloadFile local HTTP bytes");
            server.GetAwaiter().GetResult();
        }
        finally{listener.Stop();}
    }
    sealed class Engine:IBuildEngine
    {
        public readonly List<BuildErrorEventArgs> Errors=new List<BuildErrorEventArgs>();
        public readonly List<BuildWarningEventArgs> Warnings=new List<BuildWarningEventArgs>();
        public bool ContinueOnError{get{return false;}}public int LineNumberOfTaskNode{get{return 1;}}public int ColumnNumberOfTaskNode{get{return 1;}}public string ProjectFileOfTaskNode{get{return "owned.proj";}}
        public void LogErrorEvent(BuildErrorEventArgs e){Errors.Add(e);}public void LogWarningEvent(BuildWarningEventArgs e){Warnings.Add(e);}public void LogMessageEvent(BuildMessageEventArgs e){}public void LogCustomEvent(CustomBuildEventArgs e){}
        public bool BuildProjectFile(string project,string[] targets,IDictionary properties,IDictionary outputs){throw new NotSupportedException();}
    }
}
