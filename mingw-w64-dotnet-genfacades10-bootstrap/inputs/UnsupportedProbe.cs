using System;
using System.Runtime.CompilerServices;
internal static class Program {
 static int Main() {
  int count=0;
  void Expect(Action action) { try{action();throw new Exception("Expected PlatformNotSupportedException");} catch(PlatformNotSupportedException e){if(e.Message!="source genfacades fixture")throw;count++;} }
  Expect(()=>new GenFacadesFixture.Api<int>());
  Expect(()=>GenFacadesFixture.Api<int>.Echo(12));
  var api=(GenFacadesFixture.Api<int>)RuntimeHelpers.GetUninitializedObject(typeof(GenFacadesFixture.Api<int>));
  Expect(()=>{_ = api.Value;});Expect(()=>api.Value=4);
  EventHandler handler=(_,_)=>{};Expect(()=>api.Changed+=handler);Expect(()=>api.Changed-=handler);
  api.Dispose();if(count!=6) return 1;
  Console.WriteLine("PASS original unsupported generator: constructor/generic method/property/event throw exact PNSE; Dispose retained");return 0;
 }
}
