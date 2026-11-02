using System.Text;
public static class Probe
{
    public static byte[] Encode(Encoding encoding, string value) { return encoding.GetBytes(value); }
#if ENCODING13
    public static Encoding Resolve(EncodingProvider provider, int codePage) { return provider.GetEncoding(codePage); }
    public static DecoderFallback Fallback() { return new DecoderExceptionFallback(); }
#endif
}
