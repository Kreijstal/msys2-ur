using System;
using System.Linq;
using System.Reflection;

static class OwnedFixture
{
    public static void Equal(string expected,string actual)
    {
        if(!string.Equals(expected,actual,StringComparison.Ordinal))
            throw new Exception("Pager console output mismatch:\nExpected: "+expected+"\nActual: "+actual);
    }
    static int Main()
    {
        try
        {
            var tests=new PSPagerTests.BasicTests();
            var methods=tests.GetType().GetMethods(BindingFlags.Public|BindingFlags.Instance|BindingFlags.DeclaredOnly).OrderBy(m=>m.Name).ToArray();
            if(methods.Length!=4||methods.Any(m=>m.GetParameters().Length!=0))throw new Exception("unexpected Pager case inventory");
            foreach(var method in methods){method.Invoke(tests,null);Console.WriteLine("PASS upstream Pager "+method.Name);}
            var assembly=typeof(Microsoft.PowerShell.Pager).Assembly;
            if(assembly.GetName().Version!=new Version(1,0,0,0))throw new Exception("Pager identity mismatch");
            Console.WriteLine("PASS all four original Pager cases against the restored source package");
            return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error.InnerException??error);return 1;}
    }
}
