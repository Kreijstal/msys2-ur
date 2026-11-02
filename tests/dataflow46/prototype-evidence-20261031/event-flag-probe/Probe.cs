using System;
using System.Runtime.CompilerServices;
public interface I { [method: MethodImpl(MethodImplOptions.Synchronized)] event EventHandler E; }
