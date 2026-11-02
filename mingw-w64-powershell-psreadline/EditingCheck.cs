using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Microsoft.PowerShell;

namespace Test
{
    // Palette consumed by the unchanged upstream MockConsole. Only the first
    // foreground/background entries are used by that fixture.
    internal static class ReadLine
    {
        internal static readonly ConsoleColor[] Colors={ConsoleColor.DarkRed};
        internal static readonly ConsoleColor[] BackgroundColors={ConsoleColor.DarkGray};
    }
    public sealed class OwnedKeyboard
    {
        public ConsoleKeyInfo Ctrl_c=>new ConsoleKeyInfo('\x03',ConsoleKey.C,false,false,true);
    }
    public static class OwnedEditing
    {
        static ConsoleKeyInfo Key(char value)
        {
            var code=char.IsLetter(value)&&value<128?(ConsoleKey)char.ToUpperInvariant(value):value==' '?ConsoleKey.Spacebar:(ConsoleKey)0;
            return new ConsoleKeyInfo(value,code,char.IsUpper(value),false,false);
        }
        static readonly ConsoleKeyInfo Enter=new ConsoleKeyInfo('\r',ConsoleKey.Enter,false,false,false);
        static ConsoleKeyInfo Ctrl(char value)=>new ConsoleKeyInfo((char)(char.ToUpperInvariant(value)-'A'+1),(ConsoleKey)char.ToUpperInvariant(value),false,false,true);
        static ConsoleKeyInfo Special(ConsoleKey value,char text='\0')=>new ConsoleKeyInfo(text,value,false,false,false);
        static TestConsole SetConsole()
        {
            var console=new TestConsole(new OwnedKeyboard());
            var singleton=typeof(PSConsoleReadLine).GetField("_singleton",BindingFlags.Static|BindingFlags.NonPublic).GetValue(null);
            typeof(PSConsoleReadLine).GetField("_console",BindingFlags.Instance|BindingFlags.NonPublic).SetValue(singleton,console);
            return console;
        }
        public static string Run(string ownedHistory)
        {
            var console=SetConsole();
            PSConsoleReadLine.SetOptions(new SetPSReadLineOption {
                EditMode=EditMode.Emacs,HistorySaveStyle=HistorySaveStyle.SaveNothing,
                MaximumHistoryCount=100,BellStyle=BellStyle.None,PredictionSource=PredictionSource.None,
                PromptText=new[]{""},AnsiEscapeTimeout=0
            });
            if(!string.Equals(System.IO.Path.GetFullPath(PSConsoleReadLine.GetOptions().HistorySavePath),System.IO.Path.GetFullPath(ownedHistory),StringComparison.OrdinalIgnoreCase))
                throw new Exception("owned history path was not configured through the real cmdlet");
            int count=0;
            void Case(string name,string expected,params object[] input)
            {
                var keys=new List<object>();
                foreach(var item in input)
                    if(item is string text)keys.AddRange(text.Select(c=>(object)Key(c)));else keys.Add(item);
                keys.Add(Enter);console.Clear();console.Init(keys.ToArray());
                string actual=PSConsoleReadLine.ReadLine(null,null,true);
                if(console.validationFailure!=null)throw new Exception(name+" console failure",console.validationFailure);
                if(!string.Equals(actual,expected,StringComparison.Ordinal))throw new Exception(name+" expected '"+expected+"', got '"+actual+"'");
                count++;
            }
            Case("typed text","echo abc","echo abc");
            Case("cursor insertion","echo abc","echo ac",Special(ConsoleKey.LeftArrow),"b");
            Case("backspace","echo abc","echo abX",Special(ConsoleKey.Backspace,'\b'),"c");
            Case("home/end","#echo abc","echo abc",Ctrl('a'),"#",Ctrl('e'));
            Case("kill/yank","echo alpha","echo alpha",Ctrl('a'),Ctrl('k'),Ctrl('y'));
            Case("history recall","echo alpha",Special(ConsoleKey.UpArrow));
            Case("Unicode input","echo λ界","echo λ界");
            PSConsoleReadLine.SetOptions(new SetPSReadLineOption{EditMode=EditMode.Vi});
            Case("Vi delete/insert","aZc","abc",Special(ConsoleKey.Escape,'\x1b'),"hxiZ");
            if(System.IO.File.Exists(ownedHistory))throw new Exception("disabled history persistence wrote a file");
            PSConsoleReadLine.SetOptions(new SetPSReadLineOption{EditMode=EditMode.Emacs,HistorySaveStyle=HistorySaveStyle.SaveIncrementally});
            Case("owned history save","echo owned persisted line","echo owned persisted line");
            if(!System.IO.File.Exists(ownedHistory)||!System.IO.File.ReadAllLines(ownedHistory).Contains("echo owned persisted line"))
                throw new Exception("incremental history did not save the owned command");
            return "PASS "+count+" owned editing/history/Unicode/Vi/persistence cases using the unchanged original PSReadLine TestConsole and production editing algorithms";
        }
        public static string Reopen()
        {
            var console=SetConsole();
            PSConsoleReadLine.SetOptions(new SetPSReadLineOption {
                EditMode=EditMode.Emacs,HistorySaveStyle=HistorySaveStyle.SaveIncrementally,
                MaximumHistoryCount=100,BellStyle=BellStyle.None,PredictionSource=PredictionSource.None,
                PromptText=new[]{""},AnsiEscapeTimeout=0
            });
            console.Init(new object[]{Special(ConsoleKey.UpArrow),Enter});
            string result=PSConsoleReadLine.ReadLine(null,null,true);
            if(console.validationFailure!=null)throw new Exception("reopened history console failure",console.validationFailure);
            if(result!="echo owned persisted line")throw new Exception("fresh process did not recall owned persisted history: "+result);
            return "PASS a fresh process reopens and recalls the owned history file";
        }
    }
}
