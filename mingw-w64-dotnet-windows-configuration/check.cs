#pragma warning disable SYSLIB0003
using System;
using System.Collections.Generic;
using System.Configuration;
using System.Diagnostics;
using System.Diagnostics.Eventing.Reader;
using System.DirectoryServices;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Media;
using System.Reflection;
using System.Runtime.Caching;
using System.Runtime.InteropServices;
using System.Security;
using System.Security.Cryptography.X509Certificates;
using System.Security.Permissions;
using System.ServiceProcess;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Xaml.Permissions;
using System.Xml;
using Microsoft.Win32;

internal static class Program
{
    static void Require(bool ok,string text) { if(!ok)throw new Exception(text); }
    static void Throws<T>(Action a) where T:Exception { try{a();}catch(T){return;}throw new Exception("Expected "+typeof(T).Name); }
    static void Identities()
    {
        using var doc=JsonDocument.Parse(File.ReadAllText("libraries.json"));
        foreach(var lib in doc.RootElement.EnumerateArray())
        {
            string id=lib.GetProperty("id").GetString(), version=lib.GetProperty("version").GetString();
            var asm=Assembly.Load(id);
            string token=Convert.ToHexString(asm.GetName().GetPublicKeyToken()).ToLowerInvariant();
            Require(token==(lib.GetProperty("key").GetString()=="Microsoft"?"b03f5f7f11d50a3a":"cc7b13ffcd2ddd51"),"Wrong signing identity: "+id);
            Require(asm.GetName().Version==new Version(8,0,0,0),"Wrong assembly version: "+id);
            string source=id=="System.Drawing.Common"?"winforms":"runtime";
            Require(asm.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion.StartsWith(version+"+"+source+"-v8.0.31")==true,"Wrong source/version: "+id);
            Require(asm.GetManifestResourceNames().Contains("FxResources."+id+".SR.resources"),"Missing resources: "+id);
            Console.WriteLine("IDENTITY: "+asm.FullName+"; types="+asm.GetTypes().Length+"; forwards="+asm.GetForwardedTypes().Length);
        }
    }
    static void SystemEventTimer()
    {
        using var done=new ManualResetEventSlim(); IntPtr timer=IntPtr.Zero;
        TimerElapsedEventHandler handler=(sender,e)=>{if(e.TimerId==timer)done.Set();};
        SystemEvents.TimerElapsed+=handler;
        try {timer=SystemEvents.CreateTimer(100);Require(done.Wait(TimeSpan.FromSeconds(10)),"Native SystemEvents timer did not fire");}
        finally {if(timer!=IntPtr.Zero)SystemEvents.KillTimer(timer);SystemEvents.TimerElapsed-=handler;}
        Console.WriteLine("PASS: native SystemEvents timer callback, kill and unsubscription");
    }
    static void Drawing()
    {
        using var bitmap=new Bitmap(16,16);
        using(var graphics=Graphics.FromImage(bitmap)) {graphics.Clear(Color.Blue);graphics.FillRectangle(Brushes.Red,0,0,8,8);}
        Require(bitmap.GetPixel(2,2).ToArgb()==Color.Red.ToArgb(),"Native GDI+ rendering failed");
        using var encoded=new MemoryStream();bitmap.Save(encoded,ImageFormat.Png);byte[] png=encoded.ToArray();
        Require(png.Take(8).SequenceEqual(new byte[]{137,80,78,71,13,10,26,10}),"PNG encoder failed");
        using var decoded=Image.FromStream(new MemoryStream(png));
        using var copy=new Bitmap(decoded);
        Require(copy.Width==16&&copy.Height==16&&copy.GetPixel(12,12).ToArgb()==Color.Blue.ToArgb(),"PNG decode round-trip failed");
        // Resolve every Windows.Extensions drawing forward against the real implementation.
        Type[] forwards=typeof(SoundPlayer).Assembly.GetForwardedTypes();
        Require(forwards.Any(t=>t==typeof(FontConverter))&&forwards.Count(t=>!t.IsNested)==5,"Drawing type forwards missing");
        using var font=(Font)new FontConverter().ConvertFromInvariantString("Arial, 12pt");
        Require(font.SizeInPoints==12,"Forwarded font converter failed");
        using var malformed=new MemoryStream(new byte[]{1,2,3});
        Throws<ArgumentException>(()=>Image.FromStream(malformed));
        Console.WriteLine("PASS: native GDI+ draw/PNG encode-decode, drawing forwards, font conversion and malformed image");
    }
    static void WindowsExtensionsAndPermissions()
    {
        Throws<ArgumentNullException>(()=>X509Certificate2UI.DisplayCertificate(null));
        using var sound=new SoundPlayer(new MemoryStream(new byte[44]));sound.Load();Require(sound.IsLoadCompleted,"SoundPlayer loading failed");
        var level=XamlAccessLevel.AssemblyAccessTo(typeof(Program).Assembly);
        Require(level.AssemblyAccessToAssemblyName.Name==typeof(Program).Assembly.GetName().Name,"Xaml access identity lost");
        var permission=new XamlLoadPermission(level);
        Require(permission.Includes(level)&&permission.Copy()!=null,"Xaml permission compatibility failed");
        _=new SecurityPermission(PermissionState.None);
        Console.WriteLine("PASS: Windows.Extensions validation/loading and upstream .NET CAS compatibility types (no CAS enforcement)");
    }
    static void Configuration(string dir)
    {
        string file=Path.Combine(dir,"app.config");
        File.WriteAllText(file,"<configuration><appSettings><add key=\"greeting\" value=\"Grüße 世界 😀\" /></appSettings><connectionStrings><add name=\"sample\" connectionString=\"Data Source=example.invalid\" /></connectionStrings></configuration>");
        var map=new ExeConfigurationFileMap {ExeConfigFilename=file};
        var config=ConfigurationManager.OpenMappedExeConfiguration(map,ConfigurationUserLevel.None);
        Require(config.AppSettings.Settings["greeting"].Value=="Grüße 世界 😀","Configuration Unicode parse failed");
        Require(config.ConnectionStrings.ConnectionStrings["sample"].ConnectionString=="Data Source=example.invalid","Connection string parse failed");
        config.AppSettings.Settings.Add("saved","source-built");config.Save(ConfigurationSaveMode.Modified);
        Require(ConfigurationManager.OpenMappedExeConfiguration(map,ConfigurationUserLevel.None).AppSettings.Settings["saved"].Value=="source-built","Configuration save/reopen failed");
        var provider=new DpapiProtectedConfigurationProvider();
        provider.Initialize("probe",new System.Collections.Specialized.NameValueCollection{{"useMachineProtection","false"}});
        var xml=new XmlDocument();xml.LoadXml("<secret>Grüße 世界 😀</secret>");
        XmlNode encrypted=provider.Encrypt(xml.DocumentElement);
        Require(encrypted.OuterXml.IndexOf("Grüße",StringComparison.Ordinal)<0,"Configuration DPAPI encryption failed");
        Require(provider.Decrypt(encrypted).InnerText=="Grüße 世界 😀","Configuration DPAPI decrypt failed");
        string bad=Path.Combine(dir,"invalid.config");File.WriteAllText(bad,"<configuration><appSettings>");
        Throws<ConfigurationErrorsException>(()=>ConfigurationManager.OpenMappedExeConfiguration(new ExeConfigurationFileMap{ExeConfigFilename=bad},ConfigurationUserLevel.None).GetSection("appSettings"));
        Console.WriteLine("PASS: private XML configuration read/save/reopen, Unicode, connection strings, DPAPI provider and malformed XML");
    }
    static void Caching()
    {
        using var cache=new MemoryCache("msys2-"+Guid.NewGuid().ToString("N"));
        cache.Set("item","first",DateTimeOffset.MaxValue);
        Require((string)cache.AddOrGetExisting("item","second",DateTimeOffset.MaxValue)=="first","Cache atomic add failed");
        Require(cache.GetCount()==1&&(string)cache.Get("item")=="first","Cache lookup/count failed");
        cache.Set("expires","short",DateTimeOffset.UtcNow.AddMilliseconds(100));
        Require(SpinWait.SpinUntil(()=>cache.Get("expires")==null,TimeSpan.FromSeconds(5)),"Cache expiration failed");
        using var removed=new ManualResetEventSlim();CacheEntryRemovedReason reason=0;
        cache.Set("callback",42,new CacheItemPolicy{RemovedCallback=e=>{reason=e.RemovedReason;removed.Set();}});
        cache.Remove("callback");
        Require(removed.Wait(TimeSpan.FromSeconds(5))&&reason==CacheEntryRemovedReason.Removed,"Cache removal callback failed");
        Require((string)cache.Remove("item")=="first","Cache removal failed");
        Console.WriteLine("PASS: MemoryCache atomic add, values/count, expiration and removal callbacks");
    }
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern IntPtr LoadLibraryEx(string path,IntPtr file,uint flags);
    [DllImport("kernel32.dll",SetLastError=true)]static extern bool FreeLibrary(IntPtr module);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern uint FormatMessage(uint flags,IntPtr source,uint id,uint language,StringBuilder buffer,uint size,IntPtr arguments);
    static void MessageResources()
    {
        string file=Path.Combine(Path.GetDirectoryName(typeof(EventLog).Assembly.Location),"System.Diagnostics.EventLog.Messages.dll");
        IntPtr module=LoadLibraryEx(file,IntPtr.Zero,0x22);Require(module!=IntPtr.Zero,"Cannot load rebuilt event message DLL: "+Marshal.GetLastWin32Error());
        IntPtr text=Marshal.StringToHGlobalUni("source-built Grüße 世界 😀"),args=Marshal.AllocHGlobal(IntPtr.Size);
        try
        {
            Marshal.WriteIntPtr(args,text);
            foreach(uint id in new uint[]{0,1,42,65535})
            {
                var value=new StringBuilder(1024);
                uint length=FormatMessage(0x800|0x2000,module,id,0x409,value,1024,args);
                Require(length>0&&value.ToString().TrimEnd('\r','\n','\0')=="source-built Grüße 世界 😀","Native event message ID/Unicode lost: "+id+" error="+Marshal.GetLastWin32Error());
            }
        }
        finally {Marshal.FreeHGlobal(args);Marshal.FreeHGlobal(text);FreeLibrary(module);}
        Console.WriteLine("PASS: rebuilt MC/RES/managed event message DLL native FormatMessage IDs 0,1,42,65535 and Unicode insertion");
    }
    static void EventLogsAndServices()
    {
        Require(EventLog.Exists("System"),"System event log missing");
        Require(EventLogSession.GlobalSession.GetLogNames().Contains("System"),"Native event channel enumeration failed");
        using(var reader=new EventLogReader(new EventLogQuery("System",PathType.LogName,"*")))
        using(var record=reader.ReadEvent(TimeSpan.FromSeconds(5)))
            Require(record!=null&&record.ToXml().Contains("<Event"),"Native event record/XML read failed");
        Throws<EventLogNotFoundException>(()=>{using var reader=new EventLogReader("MSYS2_LogThatDoesNotExist_ConfigurationProbe");reader.ReadEvent();});
        ServiceController[] services=ServiceController.GetServices();
        try {Require(services.Any(s=>s.ServiceName.Equals("EventLog",StringComparison.OrdinalIgnoreCase)),"Native SCM enumeration failed");}
        finally {foreach(var service in services)service.Dispose();}
        using var controller=new ServiceController("EventLog");
        Require(controller.Status==ServiceControllerStatus.Running,"EventLog service is not running");
        Require(!string.IsNullOrEmpty(controller.DisplayName)&&controller.StartType!=ServiceStartMode.Disabled,"Native service configuration read failed");
        controller.Refresh();Require(controller.ServiceHandle!=null,"Native service handle missing");
        Console.WriteLine("PASS: read-only native event channels/records/XML/errors and service enumeration/status/configuration");
    }
    static void PerformanceCounters()
    {
        var categories=PerformanceCounterCategory.GetCategories();Require(categories.Length>0,"Performance categories missing");
        Require(PerformanceCounterCategory.Exists("System"),"System counter category missing");
        using var counter=new PerformanceCounter("System","System Up Time",true);
        counter.NextValue();
        Require(counter.NextValue()>0,"Native system uptime counter failed");
        Require(!string.IsNullOrWhiteSpace(counter.CounterHelp),"Counter help missing");
        counter.Close();
        Console.WriteLine("PASS: read-only native performance category enumeration, system uptime and counter help");
    }
    static void DirectoryServices()
    {
        using var entry=new DirectoryEntry("WinNT://"+Environment.MachineName+",computer");
        Require(entry.Name.Equals(Environment.MachineName,StringComparison.OrdinalIgnoreCase),"Native ADSI local WinNT computer name lost");
        Require(entry.SchemaClassName.Equals("Computer",StringComparison.OrdinalIgnoreCase),"Native ADSI class metadata lost");
        using var search=new DirectorySearcher {Filter="(objectClass=user)",PageSize=5};
        Require(search.PageSize==5&&search.Filter=="(objectClass=user)","DirectorySearcher construction failed");
        Console.WriteLine("PASS: read-only native ADSI WinNT local computer/name/class and DirectorySearcher construction");
    }
    static void CheckNativeModules(IEnumerable<string> baseline)
    {
        var allowed=new HashSet<string>(baseline.Where(x=>!string.IsNullOrWhiteSpace(x)),StringComparer.OrdinalIgnoreCase);
        using var process=Process.GetCurrentProcess();
        foreach(ProcessModule module in process.Modules)
        {
            if(module.FileName.Contains("\\Microsoft.NET\\Framework",StringComparison.OrdinalIgnoreCase))
            {
                Require(allowed.Contains(module.FileName),"Additional Framework dependency loaded: "+module.FileName);
                Console.WriteLine("OS PERFORMANCE PROVIDER BASELINE: "+module.FileName);
            }
            if(new[]{"gdiplus.dll","advapi32.dll","wevtapi.dll","activeds.dll","user32.dll"}.Contains(module.ModuleName,StringComparer.OrdinalIgnoreCase))Console.WriteLine("NATIVE: "+module.FileName);
        }
    }
    static int Main(string[] args)
    {
        if(args.Length==2&&args[0]=="--performance-check")
        {
            PerformanceCounters();CheckNativeModules(File.ReadAllLines(args[1]));
            Console.WriteLine("PASS: source-built PerformanceCounter matches native OS provider-loading baseline");return 0;
        }
        if(args.Length==2&&args[0]=="--native-mode")
        {
            string data=Path.Combine(Environment.CurrentDirectory,"diagnostic-data");Directory.CreateDirectory(data);
            switch(args[1]) {
                case "timer":SystemEventTimer();break;case "drawing":Drawing();break;
                case "config":Configuration(data);break;case "caching":Caching();break;
                case "messages":MessageResources();break;case "event-services":EventLogsAndServices();break;
                case "performance":PerformanceCounters();break;case "directory":DirectoryServices();break;
                case "identities":Identities();break;default:throw new ArgumentException("Unknown mode");
            }
            using var diagnostic=Process.GetCurrentProcess();
            foreach(ProcessModule module in diagnostic.Modules)
                if(module.FileName.Contains("\\Microsoft.NET\\Framework",StringComparison.OrdinalIgnoreCase))Console.WriteLine("FRAMEWORK LOADED: "+module.FileName);
            return 0;
        }
        string dir=Path.Combine(Environment.CurrentDirectory,"private-data");Directory.CreateDirectory(dir);
        Identities();SystemEventTimer();Drawing();WindowsExtensionsAndPermissions();Configuration(dir);Caching();MessageResources();EventLogsAndServices();DirectoryServices();
        CheckNativeModules(Array.Empty<string>());
        Console.WriteLine("PASS: source-built Windows library checks; PerformanceCounter tested separately against native OS baseline");return 0;
    }
}
