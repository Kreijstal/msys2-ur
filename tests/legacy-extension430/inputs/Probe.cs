using System;
#if REFLECTION
using System.Reflection;
public static class Probe
{
    public static Attribute Read(MemberInfo member) { return CustomAttributeExtensions.GetCustomAttribute(member, typeof(ObsoleteAttribute)); }
}
#else
using System.Text;
public static class Probe
{
    public static int Read(string value) { return new UTF8Encoding(false, true).GetByteCount(value) + new UnicodeEncoding(false, true, true).GetByteCount(value); }
#if ENCODING13
    public static int Additional(string value) { return new ASCIIEncoding().GetByteCount(value) + new UTF32Encoding(false, true, true).GetByteCount(value); }
#endif
}
#endif
