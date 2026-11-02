using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Configuration;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Text.Json;
using System.Threading.Tasks;
using System.Xml;
using System.Xml.Linq;

public sealed class ExampleSection : ConfigurationSection
{
    protected override ConfigurationPropertyCollection Properties => base.Properties;
    [ConfigurationProperty("label",DefaultValue="default-label",IsRequired=true)]
    public string Label { get=>(string)this["label"];set=>this["label"]=value; }
    [ConfigurationProperty("limit",DefaultValue=7)]
    [IntegerValidator(MinValue=1,MaxValue=50)]
    public int Limit { get=>(int)this["limit"];set=>this["limit"]=value; }
    [ConfigurationProperty("endpoint",DefaultValue="https://example.invalid/")]
    public Uri Endpoint { get=>(Uri)this["endpoint"];set=>this["endpoint"]=value; }
}

public sealed class MemorySettingsProvider : SettingsProvider
{
    static readonly Dictionary<string,object?> Values=new();
    public override string ApplicationName { get;set; }="SourceConfiguration9Check";
    public override void Initialize(string name,NameValueCollection config)=>base.Initialize("MemorySettingsProvider",config);
    public override SettingsPropertyValueCollection GetPropertyValues(SettingsContext context,SettingsPropertyCollection properties)
    {
        var result=new SettingsPropertyValueCollection();
        foreach(SettingsProperty property in properties)
            result.Add(new SettingsPropertyValue(property){SerializedValue=Values.TryGetValue(property.Name,out var value)?value:property.DefaultValue,IsDirty=false});
        return result;
    }
    public override void SetPropertyValues(SettingsContext context,SettingsPropertyValueCollection values)
    {foreach(SettingsPropertyValue value in values)Values[value.Name]=value.SerializedValue;}
}

[SettingsProvider(typeof(MemorySettingsProvider))]
public sealed class ExampleSettings : ApplicationSettingsBase
{
    [UserScopedSetting,DefaultSettingValue("initial")]
    public string Greeting {get=>(string)this[nameof(Greeting)];set=>this[nameof(Greeting)]=value;}
    [UserScopedSetting,DefaultSettingValue("7")]
    public int Count {get=>(int)this[nameof(Count)];set=>this[nameof(Count)]=value;}
}

internal static class Probe
{
    static void Need(bool value,string label){if(!value)throw new Exception(label);}
    static void Throws<T>(Action action,string label) where T:Exception
    {try{action();}catch(T){return;}throw new Exception(label);}
    static Configuration Open(string file)=>ConfigurationManager.OpenMappedExeConfiguration(new ExeConfigurationFileMap{ExeConfigFilename=file},ConfigurationUserLevel.None);
    static int Main(string[] args)
    {
        try
        {
            string root=args[0],file=Path.Combine(root,"owned.config");
            var xml=new XDocument(new XElement("configuration",
                new XElement("configSections",new XElement("section",new XAttribute("name","example"),new XAttribute("type",typeof(ExampleSection).AssemblyQualifiedName!))),
                new XElement("appSettings",new XElement("add",new XAttribute("key","greeting"),new XAttribute("value","Grüße 世界 😀 & <owned>"))),
                new XElement("connectionStrings",new XElement("add",new XAttribute("name","owned"),new XAttribute("connectionString","Data Source=fixture.invalid;Initial Catalog=世界"),new XAttribute("providerName","Owned.Source.Provider"))),
                new XElement("example",new XAttribute("label","类型 Ω"),new XAttribute("limit",13),new XAttribute("endpoint","https://example.invalid/owned"))));
            xml.Save(file);AppDomain.CurrentDomain.SetData("APP_CONFIG_FILE",file);
            var assembly=typeof(ConfigurationManager).Assembly;
            Need(assembly.GetName().Version==new Version(9,0,0,0),"Assembly version");
            Need(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="b03f5f7f11d50a3a","Microsoft identity");
            Need(Path.GetFullPath(assembly.Location)==Path.GetFullPath(Path.Combine(root,"System.Configuration.ConfigurationManager.dll")),"Exact source assembly");
            Need(assembly.GetCustomAttributesData().Any(a=>a.AttributeType.FullName=="System.Runtime.Versioning.UnsupportedOSPlatformAttribute"&&(string)a.ConstructorArguments[0].Value! =="browser"),"Original browser annotation");
            var strings=JsonSerializer.Deserialize<Dictionary<string,string>>(File.ReadAllText(Path.Combine(root,"neutral-strings.json")))!;
            var resources=new ResourceManager("FxResources.System.Configuration.ConfigurationManager.SR",assembly);
            foreach(var pair in strings)Need(resources.GetString(pair.Key,System.Globalization.CultureInfo.InvariantCulture)==pair.Value,"Resource "+pair.Key);
            var config=Open(file);Need(config.AppSettings.Settings["greeting"].Value=="Grüße 世界 😀 & <owned>","Unicode XML parse");
            Need(config.ConnectionStrings.ConnectionStrings["owned"].ProviderName=="Owned.Source.Provider","Connection strings");
            var section=(ExampleSection)config.GetSection("example");
            Need(section.Label=="类型 Ω"&&section.Limit==13&&section.Endpoint.AbsolutePath=="/owned","Typed section conversion");
            Throws<ConfigurationErrorsException>(()=>section.Limit=0,"Typed validation");
            section.Limit=21;section.Label="saved 🧪";config.AppSettings.Settings.Add("saved","source-built");
            config.Save(ConfigurationSaveMode.Modified);
            var reopened=Open(file);Need(((ExampleSection)reopened.GetSection("example")).Label=="saved 🧪"&&((ExampleSection)reopened.GetSection("example")).Limit==21,"Typed save/reopen");
            Need(reopened.AppSettings.Settings["saved"].Value=="source-built","AppSettings save");
            Need(ConfigurationManager.AppSettings["greeting"]=="Grüße 世界 😀 & <owned>","Global AppSettings");
            Need(ConfigurationManager.ConnectionStrings["owned"].ConnectionString.Contains("世界"),"Global connection strings");
            var external=Path.Combine(root,"external.config");
            File.WriteAllText(external,"<appSettings><add key=\"external\" value=\"外部 Ω\" /></appSettings>");
            var mapped=Path.Combine(root,"with-external.config");File.WriteAllText(mapped,"<configuration><appSettings configSource=\"external.config\" /></configuration>");
            Need(Open(mapped).AppSettings.Settings["external"].Value=="外部 Ω","External configSource");
            var malformed=Path.Combine(root,"malformed.config");File.WriteAllText(malformed,"<configuration><appSettings>");
            try{_=Open(malformed).AppSettings;throw new Exception("Malformed config accepted");}
            catch(ConfigurationErrorsException error){Need(string.Equals(Path.GetFullPath(error.Filename),Path.GetFullPath(malformed),StringComparison.OrdinalIgnoreCase)&&error.Line>0,"Filename/line diagnostics: actual="+error.Filename+" line="+error.Line+" expected="+malformed);}
            var integer=new IntegerValidator(1,10);integer.Validate(5);Throws<ArgumentException>(()=>integer.Validate(11),"Integer validator");
            var converter=new TimeSpanSecondsConverter();Need((TimeSpan)converter.ConvertFromInvariantString("42")! ==TimeSpan.FromSeconds(42),"TimeSpan converter");
            var setting=new ExampleSettings();int changed=0,saving=0;setting.PropertyChanged+=(s,e)=>changed++;setting.SettingsSaving+=(s,e)=>saving++;
            Need(setting.Greeting=="initial"&&setting.Count==7,"Typed setting defaults");setting.Greeting="设置 😀";setting.Count=42;setting.Save();
            var loaded=new ExampleSettings();Need(loaded.Greeting=="设置 😀"&&loaded.Count==42&&changed==2&&saving==1,"Typed settings/provider/events");
            foreach(bool machine in new[]{false,true})
            {
                var provider=new DpapiProtectedConfigurationProvider();provider.Initialize("OwnedDpapi",new NameValueCollection{{"useMachineProtection",machine?"true":"false"},{"keyEntropy","owned-entropy-Ω"}});
                var document=new XmlDocument{PreserveWhitespace=true};document.LoadXml("<owned value=\"世界 &amp; Ω\">fixture 😀</owned>");
                var encrypted=provider.Encrypt(document.DocumentElement!);Need(!encrypted.OuterXml.Contains("世界"),"DPAPI protected XML");
                Need(provider.Decrypt(encrypted).OuterXml==document.DocumentElement!.OuterXml,"DPAPI XML roundtrip");
            }
            var secureConfig=Open(file);secureConfig.AppSettings.SectionInformation.ProtectSection("DataProtectionConfigurationProvider");secureConfig.Save(ConfigurationSaveMode.Full);
            Need(!File.ReadAllText(file).Contains("Grüße"),"Protected section persistence");Need(Open(file).AppSettings.Settings["greeting"].Value=="Grüße 世界 😀 & <owned>","Protected section reopen");
            var rsa=new RsaProtectedConfigurationProvider();Throws<PlatformNotSupportedException>(()=>rsa.Encrypt(new XmlDocument()),"Original RSA Encrypt PNSE");Throws<PlatformNotSupportedException>(()=>rsa.AddKey(2048,false),"Original RSA key PNSE");
            Task.WaitAll(Enumerable.Range(0,12).Select(i=>Task.Run(()=>Need(Open(mapped).AppSettings.Settings["external"].Value=="外部 Ω","Concurrent independent loads"))).ToArray());
            GC.Collect();GC.WaitForPendingFinalizers();
            Console.WriteLine("PASS source ConfigurationManager9 identity/all resources, Unicode/typed/configSource save-reopen, global config, diagnostics, validators, settings/events, user/machine DPAPI, protected persistence, original RSA PNSE and12 concurrent loads");
            return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
}
