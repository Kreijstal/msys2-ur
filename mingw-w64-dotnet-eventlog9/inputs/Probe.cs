using System;
using System.Diagnostics;
using System.Diagnostics.Eventing.Reader;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Text.Json;
using System.Threading;
using System.Xml.Linq;

internal static class Probe
{
    static void Require(bool condition,string message) { if(!condition)throw new Exception(message); }
    static long Id(string xml) => long.Parse(XDocument.Parse(xml).Descendants().Single(x=>x.Name.LocalName=="EventRecordID").Value);
    static int Main(string[] args)
    {
        try
        {
            var assembly=typeof(EventLog).Assembly;
            Require(assembly.GetName().Version==new Version(9,0,0,0),"Assembly version");
            Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="b03f5f7f11d50a3a","Signing identity");
            Require(Path.GetFullPath(assembly.Location)==Path.GetFullPath(Path.Combine(args[0],"System.Diagnostics.EventLog.dll")),"Source asset location");
            var manager=new ResourceManager("FxResources.System.Diagnostics.EventLog.SR",assembly);
            var strings=JsonSerializer.Deserialize<System.Collections.Generic.Dictionary<string,string>>(File.ReadAllText(Path.Combine(args[0],"neutral-strings.json")))!;
            foreach(var pair in strings)Require(manager.GetString(pair.Key,System.Globalization.CultureInfo.InvariantCulture)==pair.Value,"Resource "+pair.Key);
            using var session=new EventLogSession();
            var logs=session.GetLogNames().ToArray();
            Require(logs.Contains("Application")&&logs.Contains("System"),"Log enumeration");
            Require(session.GetProviderNames().Any(),"Provider enumeration");
            using(var configuration=new EventLogConfiguration("Application",session))
                Require(configuration.LogName=="Application"&&configuration.MaximumSizeInBytes>0,"Read-only channel configuration");
            var info=session.GetLogInformation("Application",PathType.LogName);
            Require(info.RecordCount>=0,"Log information");
            var query=new EventLogQuery("Application",PathType.LogName,"*"){ReverseDirection=true,Session=session};
            long recordId;
            EventBookmark bookmark;
            using(var reader=new EventLogReader(query))
            using(var record=reader.ReadEvent(TimeSpan.FromSeconds(10)))
            {
                Require(record!=null,"Application log fixture must contain an existing record");
                recordId=record!.RecordId!.Value;bookmark=record.Bookmark;
                Require(Id(record.ToXml())==recordId,"Managed record XML");
                Require(record.ProviderName!=null&&record.LogName=="Application","Record metadata");
                _=record.Properties.Count;_=record.TimeCreated;_=record.Level;_=record.UserId;
                using var selector=new EventLogPropertySelector(new[]{"Event/System/EventRecordID","Event/System/Provider/@Name"});
                var values=((EventLogRecord)record).GetPropertyValues(selector);
                Require(Convert.ToInt64(values[0])==recordId&&Equals(values[1],record.ProviderName),"Native XPath property selection");
                using var metadata=new ProviderMetadata(record.ProviderName,session,System.Globalization.CultureInfo.CurrentCulture);
                Require(metadata.Name==record.ProviderName,"Provider metadata");
            }
            using(var reader=new EventLogReader(query,bookmark))
            {
                reader.Seek(bookmark,0);
                using var record=reader.ReadEvent();
                Require(record!=null&&record.RecordId==recordId,"Bookmark seek");
            }
            var filtered=new EventLogQuery("Application",PathType.LogName,"*[System[(EventRecordID = "+recordId+")]]"){Session=session};
            using(var reader=new EventLogReader(filtered))
            using(var record=reader.ReadEvent())Require(record!=null&&record.RecordId==recordId,"Exact record filter");
            string nativeXml=Path.Combine(args[0],"native-record.xml");
            using(var process=Process.Start(new ProcessStartInfo(args[1]){UseShellExecute=false,ArgumentList={"Application",recordId.ToString(),nativeXml}})!)
            {Require(process.WaitForExit(15000)&&process.ExitCode==0,"Independent native EvtQuery");}
            Require(Id(File.ReadAllText(nativeXml))==recordId,"Independent Win32 record ID");
            using(var classic=new EventLog("Application"))
            {
                Require(classic.Entries.Count>0,"Classic event log count");
                var last=classic.Entries[classic.Entries.Count-1];
                Require(last.Source.Length>0&&last.ReplacementStrings!=null,"Classic record properties");
            }
            bool badQuery=false;
            try{using var bad=new EventLogReader(new EventLogQuery("Application",PathType.LogName,"INVALID XPATH ["));using var record=bad.ReadEvent();}
            catch(EventLogException){badQuery=true;}
            Require(badQuery,"Invalid query propagation");
            bool badLog=false;
            try{session.GetLogInformation("Codex-Definitely-Missing-Log-9",PathType.LogName);}
            catch(EventLogException){badLog=true;}
            Require(badLog,"Missing log propagation");
            using(var delivered=new ManualResetEventSlim())
            using(var watcher=new EventLogWatcher(filtered,null,true))
            {
                Exception? failure=null;
                watcher.EventRecordWritten+=(sender,e)=>{try{if(e.EventException!=null)throw e.EventException;using var record=e.EventRecord;Require(record!=null&&record.RecordId==recordId,"Watcher record");}catch(Exception error){failure=error;}finally{delivered.Set();}};
                watcher.Enabled=true;
                Require(delivered.Wait(TimeSpan.FromSeconds(15)),"Existing event callback");
                watcher.Enabled=false;
                if(failure!=null)throw failure;
            }
            for(int i=0;i<20;i++)
            {
                using var reader=new EventLogReader(filtered);
                using var record=reader.ReadEvent();
                Require(record?.RecordId==recordId,"Repeated native handle lifetime");
                if(i%4==0){GC.Collect();GC.WaitForPendingFinalizers();}
            }
            Console.WriteLine("PASS source EventLog9 identity/all41 strings, classic/modern reads, metadata, XPath, bookmarks, native crosscheck, errors, callback and20 GC/disposal iterations");
            return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
}
