using System;
using System.Reflection;
using System.Runtime.Loader;
internal static class Program {
 static int Main(string[] args) {
  var assembly=AssemblyLoadContext.Default.LoadFromAssemblyPath(System.IO.Path.GetFullPath(args[0]));
  var tfa=assembly.GetCustomAttribute<System.Runtime.Versioning.TargetFrameworkAttribute>()!.FrameworkName;
  if(tfa!=".NETStandard,Version=v2.0")throw new Exception("Original Standard2 consumer profile");
  var wc=assembly.GetType("Wcwidth.UnicodeCalculator")!;
  if(wc.IsPublic!=(args[1]=="public"))throw new Exception("Source visibility guard");
  int count=(int)assembly.GetType("ScalarCheck")!.GetMethod("Run")!.Invoke(null,null)!;
  Console.WriteLine("PASS actual NS2 source consumer, "+count+" Unicode-version/scalar cases, "+args[1]+" visibility");return 0;
 }
}
