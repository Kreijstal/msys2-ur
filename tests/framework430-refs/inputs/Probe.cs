using System;
public static class Probe
{
#if COLLECTIONS
    public static int Read() { var values = new System.Collections.Generic.List<int>(); values.Add(42); return values[0]; }
#elif PROBE_DEBUG
    public static void Read() { System.Diagnostics.Debug.WriteLine("source reference consumer"); }
#elif TOOLS
    public static Type Read() { return typeof(System.Diagnostics.CodeAnalysis.SuppressMessageAttribute); }
#elif GLOBALIZATION
    public static string Read() { return System.Globalization.CultureInfo.InvariantCulture.Name; }
#elif NET
    public static string Read() { return new System.Net.NetworkCredential("source", "local-test").UserName; }
#elif RESOURCES
    public static Type Read() { return typeof(System.Resources.ResourceManager); }
#elif HANDLES
    public static bool Read(System.Runtime.InteropServices.SafeHandle handle) { return handle.IsClosed; }
#elif TIMER
    public static System.Threading.Timer Read(System.Threading.TimerCallback callback) { return new System.Threading.Timer(callback, null, -1, -1); }
#endif
}
