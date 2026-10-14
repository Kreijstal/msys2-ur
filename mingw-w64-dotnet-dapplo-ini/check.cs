using System;
using System.IO;
using System.ComponentModel;
using Dapplo.Ini;
using Dapplo.Ini.Attributes;
using Dapplo.Ini.Interfaces;
[IniSection("Packaging")]
public interface IPackagingSettings:IIniSection,INotifyPropertyChanged {int Count {get;set;}string Name {get;set;}}
class Check {static void Main(){var dir=Path.Combine(Path.GetTempPath(),"dapplo-package-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(dir);try{IniConfigRegistry.Clear();using(var config=IniConfigRegistry.ForFile("test.ini").AddSearchPath(dir).RegisterSection<IPackagingSettings>(new PackagingSettingsImpl()).Build()){var section=config.GetSection<IPackagingSettings>();int changes=0;section.PropertyChanged+=(s,e)=>changes++;section.Count=42;section.Name="Greenshot λ 🐾";if(changes!=2)throw new Exception("generated change notifications");config.Save();}IniConfigRegistry.Clear();using(var config=IniConfigRegistry.ForFile("test.ini").AddSearchPath(dir).RegisterSection<IPackagingSettings>(new PackagingSettingsImpl()).Build()){config.Load();var section=config.GetSection<IPackagingSettings>();if(section.Count!=42||section.Name!="Greenshot λ 🐾")throw new Exception("generated settings/save/load Unicode round trip");}Console.WriteLine("PASS Dapplo.Ini original source generator, typed properties, notifications and Unicode file persistence");}finally{IniConfigRegistry.Clear();Directory.Delete(dir,true);}}}
