using System;
public static class Extensions
{
    extension(string text)
    {
        public int TwiceLength => text.Length * 2;
    }
}
public static class Probe
{
    public static int Main()
    {
        if ("abc".TwiceLength != 6 || GeneratedNumber.Value != 42)
            throw new Exception("CSharp14 or original compiler source generator failed");
        Console.WriteLine("PASS source Compiler5 CSharp14 extension property, generator output=42 and emitted execution");
        return 0;
    }
}
