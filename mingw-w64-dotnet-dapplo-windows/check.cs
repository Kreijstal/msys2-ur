using System;
using System.IO;
using System.Reflection;
using Dapplo.Windows.Common.Structs;
using Dapplo.Windows.User32;
using Dapplo.Windows.Gdi32;
using Dapplo.Windows.Gdi32.SafeHandles;
class Check {[STAThread] static void Main(){int assemblies=0,types=0;foreach(var file in Directory.GetFiles(AppContext.BaseDirectory,"Dapplo.Windows*.dll")){types+=Assembly.LoadFrom(file).GetTypes().Length;assemblies++;}if(assemblies!=16||types<100)throw new Exception("complete source assembly/type loading");var rect=new NativeRect(4,8,24,28);System.Drawing.Rectangle drawing=rect;NativeRect copy=drawing;if(rect.Width!=24||rect.Height!=28||!rect.Equals(copy)||rect.GetHashCode()!=copy.GetHashCode())throw new Exception("native/drawing geometry and hash");if(User32Api.GetDesktopWindow()==IntPtr.Zero)throw new Exception("real User32 interop");var window=SafeWindowDcHandle.FromDesktop();var memory=Gdi32Api.CreateCompatibleDC(window);if(window.IsInvalid||memory.IsInvalid)throw new Exception("GDI compatible context");memory.Dispose();window.Dispose();if(!window.IsClosed||!memory.IsClosed)throw new Exception("native GDI ownership");Console.WriteLine($"PASS Dapplo.Windows {assemblies} assemblies/{types} types, native geometry, User32 and GDI creation/disposal");}}
