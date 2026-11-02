using System;
public static class Probe
{
    public static Guid Parse(string text) { return Guid.Parse(text); }
    public static T Identity<T>(T value) where T : class { return value; }
#if COMPACTION
    public static System.Runtime.GCLargeObjectHeapCompactionMode Compact() { return System.Runtime.GCLargeObjectHeapCompactionMode.CompactOnce; }
#endif
#if RUNTIME15
    public static char Delimiter() { return Type.Delimiter; }
#endif
}
