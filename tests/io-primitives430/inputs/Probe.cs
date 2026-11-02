#if PRIMITIVES
using System.Reflection;
public static class Probe
{
    public static MethodAttributes Flags() { return MethodAttributes.Public | MethodAttributes.Static; }
    public static TypeAttributes TypeFlags() { return TypeAttributes.Public | TypeAttributes.Sealed; }
}
#else
using System.IO;
public static class Probe
{
    public static int Read(Stream stream, byte[] buffer) { return stream.Read(buffer, 0, buffer.Length); }
    public static string ReadText(TextReader reader) { return reader.ReadToEnd(); }
#if IO15
    public static Stream Buffer(Stream stream) { return new BufferedStream(stream); }
#endif
}
#endif
