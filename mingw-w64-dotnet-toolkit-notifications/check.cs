using System;
using Microsoft.Toolkit.Uwp.Notifications;
using Windows.Data.Xml.Dom;
using Windows.UI.Notifications;
class Program {
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static void Main(){
        var args=new ToastArguments();args.Add("text","λ & 漢字");
        Require(ToastArguments.Parse(args.ToString())["text"]=="λ & 漢字","toolkit argument encoding");
        var content=new ToastContentBuilder().AddArgument("id",42).AddText("Source bootstrap λ").AddText("漢字 & XML").GetToastContent();
        var toast=new ToastNotification(content.GetXml());
        var data=new NotificationData();data.Values["progress"]="42";data.SequenceNumber=7;toast.Data=data;
        Require(toast.Data.Values["progress"]=="42" && toast.Data.SequenceNumber==7,"native property map");
        void Activated(ToastNotification sender,object a){}
        toast.Activated+=Activated;toast.Activated-=Activated;
        Require(toast.Content.GetXml().Contains("漢字 &amp; XML"),"native toast XML");
        Console.WriteLine("PASS toolkit content, native toast object, maps and event registration");
        GC.Collect();GC.WaitForPendingFinalizers();
    }
}
