using System;
using System.Collections.Generic;
using System.Numerics;
using System.Runtime.InteropServices;
internal static class Program {
 static int Main() {
  if(Environment.Version!=new Version(10,0,5))return 1;
  var order=new OrderedDictionary<string,int>();order.Add("λ",7);order.Add("second",3);if(order.GetAt(0).Key!="λ"||order["λ"]!=7)return 2;
  var priority=new PriorityQueue<string,int>();priority.Enqueue("second",2);priority.Enqueue("first",1);if(priority.Dequeue()!="first")return 3;
  var uri=new Uri("https://example.invalid/a/../λ?q=1");if(uri.Host!="example.invalid"||!uri.AbsolutePath.Contains("%CE%BB"))return 4;
  int[] values={1,2,3,4};var memory=new Memory<int>(values,1,2);memory.Span[0]=9;if(values[1]!=9||memory.Length!=2)return 5;
  if((new Vector<int>(3)+new Vector<int>(4))[0]!=7)return 6;
  try {order.Add("λ",4);return 7;}catch(ArgumentException e){if(e.Message.Contains("Arg_AddingDuplicateWithKey"))return 8;}
  return 0;
 }
}
