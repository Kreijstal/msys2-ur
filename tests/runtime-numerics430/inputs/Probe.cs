using System;
using System.Numerics;
public static class Probe
{
    public static BigInteger Integer(string value) { return BigInteger.Parse(value); }
    public static Complex Number(double real,double imaginary) { return new Complex(real,imaginary); }
    public static int Main()
    {
        BigInteger value=BigInteger.Pow(new BigInteger(7),80);
        if(BigInteger.Parse(value.ToString())!=value || BigInteger.ModPow(new BigInteger(3),new BigInteger(100),new BigInteger(97))!=81) throw new Exception("Original BigInteger contract");
        Complex result=Number(2,3)*Number(2,-3);if(result.Real!=13 || result.Imaginary!=0) throw new Exception("Original Complex contract");return 0;
    }
}
