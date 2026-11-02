using System;
namespace Microsoft.VisualStudio.TestTools.UnitTesting
{
 [AttributeUsage(AttributeTargets.Class)] public sealed class TestClassAttribute:Attribute {}
 [AttributeUsage(AttributeTargets.Method)] public sealed class TestMethodAttribute:Attribute {}
 [AttributeUsage(AttributeTargets.Method,AllowMultiple=true)] public sealed class TestCategoryAttribute:Attribute { public TestCategoryAttribute(string name){} }
 public static class Assert
 {
  public static void AreEqual<T>(T expected,T actual,string message=null){if(!object.Equals(expected,actual))throw new Exception((message??"Equality failed")+"\nExpected: "+expected+"\nActual: "+actual);}
  public static void Fail(string message){throw new Exception(message);}
 }
}
