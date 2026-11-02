using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Threading;
static class Probe
{
 static int Main()
 {
  var values=new List<int>{1,2,3};using(var local=new ThreadLocal<int>(()=>values.Count))if(local.Value!=3)throw new Exception("Original collections/threading contracts");
  IIdentity identity=new Identity();if(!identity.IsAuthenticated || identity.Name!="source-contract-probe")throw new Exception("Original principal contract");
  if(Marshal.SizeOf(typeof(int))!=4 || Environment.Version.Major!=8)throw new Exception("Original Interop/Runtime contracts on source NET8");
  return 0;
 }
 sealed class Identity:IIdentity {public string Name=>"source-contract-probe";public string AuthenticationType=>"source";public bool IsAuthenticated=>true;}
 public static int UnsafeBindingOnly()=>Unsafe.SizeOf<int>();
}
