using System;
using System.Linq;
using System.IO;
using log4net.Layout;
using log4net.Repository.Hierarchy;
using System.Xml;
using log4net;
using log4net.Appender;
using log4net.Config;
class Check {static void Main(){var repository=LogManager.CreateRepository("Greenshot-packaging");var xml=new XmlDocument();xml.LoadXml("<log4net><appender name='buffer' type='log4net.Appender.MemoryAppender'/><root><level value='DEBUG'/><appender-ref ref='buffer'/></root></log4net>");XmlConfigurator.Configure(repository,xml.DocumentElement);var log=LogManager.GetLogger(repository.Name,"Greenshot");log.Info("λ 🐾");log.Error("failure",new InvalidOperationException("detail"));var appender=(MemoryAppender)repository.GetAppenders().Single();var entries=appender.GetEvents();if(entries.Length!=2||entries[0].RenderedMessage!="λ 🐾"||entries[0].Level.Name!="INFO"||entries[1].ExceptionObject.Message!="detail")throw new Exception("XML configuration, logging levels, Unicode and exception event preservation");var dir=Path.Combine(Path.GetTempPath(),"log4net-package-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(dir);try{var rolling=new RollingFileAppender{File=Path.Combine(dir,"capture.log"),AppendToFile=true,RollingStyle=RollingFileAppender.RollingMode.Size,MaximumFileSize="1KB",MaxSizeRollBackups=2,StaticLogFileName=true,Layout=new PatternLayout("%message%newline")};rolling.ActivateOptions();((Hierarchy)repository).Root.AddAppender(rolling);for(int i=0;i<30;i++)log.Info("rolling-"+i+new string('x',100));LogManager.ShutdownRepository(repository.Name);var files=Directory.GetFiles(dir);if(files.Length<2||!files.Any(f=>File.ReadAllText(f).Contains("rolling-29")))throw new Exception("real rolling-file open/count/rotation");}finally{LogManager.ShutdownRepository(repository.Name);Directory.Delete(dir,true);}Console.WriteLine("PASS log4net real XML configuration, appender/repository, Unicode/error events, real size-based file rotation and teardown");}}
