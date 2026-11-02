using System;
using System.Reflection;
public static class Probe
{
    public static string Name(AssemblyName name) { return name.Name; }
    public static Type AttributeType(CustomAttributeData data) { return data.AttributeType; }
#if REFLECTION15
    public static BindingFlags Flags() { return BindingFlags.Public | BindingFlags.Instance; }
    public static bool Filter(MemberInfo member, MemberFilter filter) { return filter(member, null); }
#endif
}
