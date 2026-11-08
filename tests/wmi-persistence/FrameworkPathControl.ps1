$ErrorActionPreference = 'Stop'
Add-Type -ReferencedAssemblies System.Management -TypeDefinition @'
using System;
using System.Management;
using System.Threading;
public static class FrameworkPathControl {
 public static void Run() {
  string name="MSYS2_WmiPathControl_"+Guid.NewGuid().ToString("N");
  var root=new ManagementScope("root");root.Connect();bool created=false;
  string ns="__Namespace.Name=\""+name+"\"";
  try {
   using(var type=new ManagementClass(root,new ManagementPath("__Namespace"),null))
   using(var row=type.CreateInstance()){row["Name"]=name;row.Put();created=true;}
   var scope=new ManagementScope("root\\"+name);scope.Connect();
   using(var type=new ManagementClass(scope,new ManagementPath(),null)){
    type["__CLASS"]="MSYS2_Control";type.Properties.Add("Id",CimType.String,false);type.Properties["Id"].Qualifiers.Add("Key",true);type.Put();
    using(var row=type.CreateInstance()){
     row["Id"]="owned";var path=row.Put();
     using(var reopened=new ManagementObject(scope,path,null)){
      reopened.Get();var observer=new ManagementOperationObserver();
      using(var done=new ManualResetEvent(false)){
       string result=null;bool instance=false;ManagementStatus status=ManagementStatus.Failed;
       observer.ObjectPut+=delegate(object sender,ObjectPutEventArgs args){result=args.Path.RelativePath;instance=args.Path.IsInstance;};
       observer.Completed+=delegate(object sender,CompletedEventArgs args){status=args.Status;done.Set();};
       reopened.Put(observer,new PutOptions{Type=PutType.UpdateOnly});
       if(!done.WaitOne(30000)||status!=ManagementStatus.NoError)throw new Exception("Framework async Put failed");
       Console.WriteLine("FRAMEWORK_CONTROL ObjectPut.RelativePath="+result+" IsInstance="+instance);
      }
     }
    }
   }
  }finally{if(created)using(var row=new ManagementObject(root,new ManagementPath(ns),null)){row.Delete();Console.WriteLine("REMOVED "+name);}}
 }
}
'@
[FrameworkPathControl]::Run()
