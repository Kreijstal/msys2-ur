using System;
using Wcwidth;
public static class ScalarCheck {
 public static int Run() {
  int count=0;
  foreach(Unicode version in Enum.GetValues(typeof(Unicode)))
   foreach(var pair in new[]{(0,0),(0x1b,-1),(0x7f,-1),(0x41,1),(0x0301,0),(0x200d,0),(0x4e16,2)}) {
    if(UnicodeCalculator.GetWidth(pair.Item1,version)!=pair.Item2)throw new Exception("Width mismatch "+version+"/"+pair.Item1);count++;
   }
  return count;
 }
}
