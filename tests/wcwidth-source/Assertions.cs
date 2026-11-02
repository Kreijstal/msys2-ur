using System;
using System.Collections.Generic;
using System.Linq;
namespace Xunit { [AttributeUsage(AttributeTargets.Method)] public sealed class FactAttribute : Attribute {} }
namespace Shouldly {
 public static class Assertions {
  public static void ShouldBe(this int actual,int expected) {if(actual!=expected)throw new Exception($"Expected {expected}, actual {actual}");}
  public static void ShouldBe<T>(this IEnumerable<T> actual,IEnumerable<T> expected) {if(!actual.SequenceEqual(expected))throw new Exception("Sequence assertion failed");}
 }
}
