using System;
using System.Runtime.InteropServices.JavaScript;

internal static class JavaScriptWindowsProbe
{
    private static void Unsupported(Action action)
    {
        try { action(); }
        catch (PlatformNotSupportedException error)
        {
            if (error.Message != "System.Runtime.InteropServices.JavaScript is not supported on this platform.")
                throw new Exception("Original platform resource message differs", error);
            return;
        }
        throw new Exception("Expected the original Windows unsupported-platform behavior");
    }

    private static void Main()
    {
        Unsupported(() => { _ = JSHost.GlobalThis; });
        Unsupported(() => { _ = JSHost.DotnetInstance; });
        Unsupported(() => { _ = new JSException("source10"); });
        Console.WriteLine("PASS original JavaScript Windows contract APIs throw PNSE with the original resource message");
    }
}
