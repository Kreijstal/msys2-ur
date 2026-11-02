using System;
public static class Probe
{
#if WIN32
    public static int Read() { return new System.ComponentModel.Win32Exception(5).NativeErrorCode; }
#elif CONSOLE
    public static void Read() { System.Console.WriteLine("source reference consumer"); }
#elif TRACING
    public static Type Read() { return typeof(System.Diagnostics.Tracing.EventSource); }
#elif CALENDARS
    public static int Read() { return new System.Globalization.GregorianCalendar().GetDaysInYear(2000); }
#elif FILESYSTEM
    public static bool Read() { return System.IO.File.Exists("source-reference-test"); }
#elif SOCKETS
    public static System.Net.Sockets.Socket Read() { return new System.Net.Sockets.Socket(System.Net.Sockets.SocketType.Stream, System.Net.Sockets.ProtocolType.Tcp); }
#elif EXTENSIONS
    public static int Read() { return System.Math.Abs(-42); }
#endif
}
