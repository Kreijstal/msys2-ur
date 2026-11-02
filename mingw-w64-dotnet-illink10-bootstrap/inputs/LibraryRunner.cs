using System;
using System.Reflection;
using System.Text;
class Program {
 static void Main(string[] args){var a=Assembly.LoadFrom(args[0]);var derived=a.GetType("Derived")!;if((string)derived.GetProperty("Text")!.GetValue(Activator.CreateInstance(derived))!="π λ")throw new Exception("Linked virtual override");var value=a.GetType("Value`1")!.MakeGenericType(typeof(StringBuilder));if(value.GetMethod("Read")!.Invoke(Activator.CreateInstance(value),null) is not StringBuilder)throw new Exception("Linked generic interface/constraint");Console.WriteLine("PASS linked library virtual/interface/generic execution");}
}
