using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Serialization.Formatters.Binary;
using System.Security.Cryptography;
using System.Text;
using Greenshot.Base.Core;
using Greenshot.Editor.Drawing;

[Serializable] sealed class Graph { public Graph Next; public List<string> Items; }
[Serializable] sealed class Disallowed { public int Value = 17; }
static class Program {
 static void Require(bool condition, string message) { if (!condition) throw new Exception(message); }
 [STAThread] static void Main() {
  var graph=new Graph { Items=new List<string>{"source-built", "Greenshot"} };graph.Next=graph;
  var clone=ObjectExtensions.Clone(graph);
  Require(!ReferenceEquals(graph,clone)&&ReferenceEquals(clone,clone.Next)&&clone.Items.SequenceEqual(graph.Items),"deep clone graph");
  string text="Greenshot configuration: source-built 2026";
  string encrypted=StringExtensions.Encrypt(text);
  Require(encrypted!=text&&StringExtensions.Decrypt(encrypted)==text,"configuration encryption roundtrip");
  using(var aes=Aes.Create()) {
   using var output=new MemoryStream();
   using(var crypto=new CryptoStream(output,aes.CreateEncryptor(Encoding.ASCII.GetBytes("lsjvkwhvwujkagfauguwcsjgu2wueuff"),Encoding.ASCII.GetBytes("dlgjowejgogkklwj")),CryptoStreamMode.Write)) {
    byte[] bytes=Encoding.ASCII.GetBytes(text);crypto.Write(bytes,0,bytes.Length);crypto.FlushFinalBlock();
   }
   Require(encrypted==Convert.ToBase64String(output.ToArray()),"legacy configuration cipher compatibility");
  }
  Console.WriteLine("PASS: deep clone cycles and legacy-compatible configuration encryption");
  IniConfigHelper.EnsureInitialized();
  IniConfigHelper.EnsureSection<Greenshot.Editor.Configuration.IEditorConfiguration>(() => new Greenshot.Editor.Configuration.EditorConfigurationImpl());
  using var bitmap=new Bitmap(64,48);bitmap.SetPixel(4,5,Color.CornflowerBlue);
  using var surface=new Surface(bitmap);
  var rectangle=new RectangleContainer(surface){Left=7,Top=9,Width=23,Height=17};
  surface.AddElement(rectangle,false,false);
  var elements=new DrawableContainerList{rectangle};
  byte[] serialized=DrawableContainerClipboard.Serialize(elements);
  var read=DrawableContainerClipboard.Deserialize(serialized);
  Require(read!=null&&read.Count==1&&read[0] is RectangleContainer&&read[0].Left==7&&read[0].Width==23,"clipboard element roundtrip");
  using var bad=new MemoryStream();new BinaryFormatter().Serialize(bad,new Disallowed());
  Require(DrawableContainerClipboard.Deserialize(bad.ToArray())==null,"clipboard binder must reject unknown types");
  using var stream=new MemoryStream();Require(surface.SaveElementsToStream(stream)>0,"save editor elements");stream.Position=0;
  using var other=new Surface(new Bitmap(64,48));other.LoadElementsFromStream(stream);
  Require(other.Elements.Count==1&&other.Elements[0].Top==9&&other.Elements[0].Height==17,"load editor elements");
  Console.WriteLine("PASS: actual editor surface, drawing elements, clipboard serialization and whitelist rejection");
  foreach(string name in new[]{"Greenshot.Base","Greenshot.Editor","Greenshot"}) {
   var assembly=Assembly.Load(name);Console.WriteLine("PASS: type closure "+name+": "+assembly.GetTypes().Length+" types");
  }
  var app=Assembly.Load("Greenshot");
  Require(app.GetCustomAttributes<AssemblyMetadataAttribute>().Any(a=>a.Key=="GreenshotEdition"&&a.Value=="Full"),"Full edition");
  Console.WriteLine("PASS: full edition metadata");
  string mutexName="GreenshotPortCheck-"+Guid.NewGuid();
  using(var owned=Greenshot.Helpers.ResourceMutex.Create(mutexName,"port check",false)) {
   Require(owned.IsLocked,"first application mutex acquisition");
   bool secondLocked=true;
   var thread=new System.Threading.Thread(()=> {using var second=Greenshot.Helpers.ResourceMutex.Create(mutexName,"port check",false);secondLocked=second.IsLocked;});
   thread.Start();thread.Join();Require(!secondLocked,"contending application mutex");
  }
  using(var next=Greenshot.Helpers.ResourceMutex.Create(mutexName,"port check",false))Require(next.IsLocked,"application mutex acquisition after release");
  Console.WriteLine("PASS: application mutex DACL, contention and reacquisition");
  Exception nativeError=null;
  var nativeThread=new System.Threading.Thread(()=> {
   try {
    var interop=typeof(ObjectExtensions).Assembly.GetType("Greenshot.Base.Native.WindowsGraphicsCaptureInterop",true);
    var create=interop.GetMethods(BindingFlags.Static|BindingFlags.NonPublic).Single(m=>m.Name=="CreateD3D11Device"&&m.GetParameters().Length==3);
    object[] args={5,null,null};
    System.Runtime.InteropServices.Marshal.ThrowExceptionForHR((int)create.Invoke(null,args));
    var wrap=interop.GetMethod("CreateID3DDeviceFromD3D11Device",BindingFlags.Static|BindingFlags.NonPublic);
    var projected=wrap.Invoke(null,new[]{args[1]});Require(projected!=null,"WinRT Direct3D device");
    (projected as IDisposable)?.Dispose();
    System.Runtime.InteropServices.Marshal.ReleaseComObject(args[2]);
    System.Runtime.InteropServices.Marshal.ReleaseComObject(args[1]);
   } catch(Exception ex) {nativeError=ex;}
  });nativeThread.SetApartmentState(System.Threading.ApartmentState.MTA);nativeThread.Start();nativeThread.Join();
  if(nativeError!=null)throw new Exception("native D3D11 projection",nativeError);
  Console.WriteLine("PASS: native WARP D3D11 device and WinRT Direct3D projection");
  using var form=new System.Windows.Forms.Form();
  var factory=Greenshot.Native.DataTransferManagerHelper.GetInteropFactory("Windows.ApplicationModel.DataTransfer.DataTransferManager");
  var iid=new Guid("a5caee9b-8708-49d1-8d36-67d25a8da00c");
  IntPtr pointer=factory.GetForWindow(form.Handle,ref iid);
  try { Require(WinRT.MarshalInterface<Windows.ApplicationModel.DataTransfer.DataTransferManager>.FromAbi(pointer)!=null,"DataTransferManager for HWND"); }
  finally {if(pointer!=IntPtr.Zero)System.Runtime.InteropServices.Marshal.Release(pointer);System.Runtime.InteropServices.Marshal.ReleaseComObject(factory);}
  Console.WriteLine("PASS: native Share manager factory and HWND projection");
 }
}
