using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Shouldly;
internal static class Program {
 static int Main() {
  bool negativeRejected=false;try{1.ShouldBe(2);}catch(Exception){negativeRejected=true;}
  if(!negativeRejected)throw new Exception("Assertion negative control failed");
  int count=0;
  foreach(var type in Assembly.GetExecutingAssembly().GetTypes().Where(t=>t.Namespace=="Wcwidth.Tests" && t.IsClass))
   foreach(var method in type.GetMethods(BindingFlags.Public|BindingFlags.Instance|BindingFlags.DeclaredOnly).Where(m=>m.GetCustomAttributes().Any(a=>a.GetType().FullName=="Xunit.FactAttribute"))) {
    method.Invoke(Activator.CreateInstance(type),null);count++;
   }
  if(count==0)throw new Exception("No upstream fixtures executed");
  Console.WriteLine("PASS "+count+" unchanged upstream Fact methods; assertion negative control");return 0;
 }
}
