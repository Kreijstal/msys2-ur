using System;
using System.Reflection;
internal static class Program {
 static int Main(string[] args) {
  if(Environment.Version!=new Version(10,0,5))return 1;
  int count=0;
  foreach(var path in args){var assembly=Assembly.LoadFrom(path);var types=assembly.GetForwardedTypes();if(types.Length==0)return 2;foreach(var type in types){if(type.Assembly!=typeof(object).Assembly)return 3;count++;}}
  return count>20?0:4;
 }
}
