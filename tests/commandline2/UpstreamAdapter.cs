using System;
using System.Collections.Generic;
using System.Linq;
namespace Xunit {
 [AttributeUsage(AttributeTargets.Method)] public class FactAttribute:Attribute {}
 [AttributeUsage(AttributeTargets.Method)] public class TheoryAttribute:Attribute {}
 [AttributeUsage(AttributeTargets.Method,AllowMultiple=true)] public class InlineDataAttribute:Attribute {public object[] Data;public InlineDataAttribute(params object[] data){Data=data;}}
}
namespace Xunit.Abstractions { public interface ITestOutputHelper { void WriteLine(string text); } }
namespace FluentAssertions {
 public sealed class StringSequenceAssertions {public IEnumerable<string> Subject;public StringSequenceAssertions(IEnumerable<string> value){Subject=value;}}
 public static class Adapter {public static StringSequenceAssertions Should(this IEnumerable<string> value)=>new(value);}
}
namespace System.CommandLine.Tests.Utility {
 public static class Adapter {
  public static void BeEquivalentSequenceTo(this FluentAssertions.StringSequenceAssertions actual,params object[] expected){var values=actual.Subject.Cast<object>().ToArray();if(!values.SequenceEqual(expected))throw new Exception("Upstream strict string sequence assertion failed");}
 }
}
