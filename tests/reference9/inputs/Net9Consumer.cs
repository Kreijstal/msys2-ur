using System;
using System.Linq;
using System.Threading;
internal static class Program
{
    public static int Main()
    {
        var gate = new Lock();
        int sum;
        lock (gate) sum = new[] { "λ", "世界", "λ" }.CountBy(s => s).Sum(p => p.Value);
        Console.WriteLine("source9 Lock/CountBy contracts: " + sum);
        return sum == 3 ? 0 : 1;
    }
}
