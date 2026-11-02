using System;
using System.Diagnostics.CodeAnalysis;
using System.Linq;
using System.Reflection;
using System.Text;
internal static class Program
{
 [DynamicDependency(DynamicallyAccessedMemberTypes.PublicMethods,typeof(ReflectionKept))]
 static int Main()
 {
  var method=typeof(ReflectionKept).GetMethod("Value",BindingFlags.Public|BindingFlags.Static)!;
  if((int)method.Invoke(null,null)!=42 || Kept<int>.Value(42)!=42)throw new Exception("Required reflection/generic code lost");
  using var s=Assembly.GetExecutingAssembly().GetManifestResourceStream("Owned.Resource")!;
  using var r=new System.IO.StreamReader(s,Encoding.UTF8);if(r.ReadToEnd()!="π λ source resource\n")throw new Exception("Resource payload changed");
  if(!new[]{20,22}.Select(x=>x).Sum().Equals(42))throw new Exception("Framework references failed");
  Console.WriteLine("PASS linked reflection/generics/Unicode resource/framework execution");return 0;
 }
}
public static class ReflectionKept{public static int Value()=>42;}
public static class Kept<T>{public static T Value(T value)=>value;}
internal static class UnusedInternal{public static int Dead()=>-1;}
