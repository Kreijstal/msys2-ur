extern alias candidate;
using System;
using System.Globalization;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.Loader;
using B=candidate::System.Numerics.BigInteger;
using C=candidate::System.Numerics.Complex;

static class Program
{
    static int Checks;
    static void Require(bool value,string message){Checks++;if(!value)throw new Exception(message);}
    static B Next(Random random,int bytes)
    {
        byte[] value=new byte[bytes];random.NextBytes(value);return new B(value);
    }
    static void Main()
    {
        string location=typeof(B).Assembly.Location.Replace('\\','/');
        Require(typeof(B).Assembly==typeof(C).Assembly && location.EndsWith("/System.Runtime.Numerics.dll") && !location.Contains("/shared/"),"Actual candidate runtime implementation must execute");
        Require(typeof(B).Assembly.GetName().Version==new Version(4,0,2,0),"Original runtime identity");
        Require(!typeof(B).Assembly.CustomAttributes.Any(a=>a.AttributeType.FullName=="System.Runtime.CompilerServices.ReferenceAssemblyAttribute"),"Candidate must contain executable implementation");
        for(int x=-40;x<=40;x++)for(int y=-17;y<=17;y++)
        {
            B a=x,b=y;Require((long)(a+b)==(long)x+y,"small add");Require((long)(a-b)==(long)x-y,"small subtract");Require((long)(a*b)==(long)x*y,"small multiply");
            if(y!=0){B q=B.DivRem(a,b,out B rem);Require((long)q==x/y && (long)rem==x%y,"signed divide/remainder");}
        }
        var random=new Random(734310);
        foreach(int size in new[]{1,7,31,64,129,257,521})for(int iteration=0;iteration<8;iteration++)
        {
            B a=Next(random,size),b=Next(random,Math.Max(1,size/2));if(b.IsZero)b=B.One;
            Require(a+b-b==a && a-b+b==a,"large add/subtract inverse");Require(a*b==b*a,"large multiplication commutes");
            B q=B.DivRem(a,b,out B rem);Require(q*b+rem==a && B.Abs(rem)<B.Abs(b),"large signed division identity");
            Require(new B(a.ToByteArray())==a,"two's-complement byte round trip");
            Require(B.Parse(a.ToString(CultureInfo.InvariantCulture),CultureInfo.InvariantCulture)==a,"large invariant decimal round trip");
            Require(B.Parse(a.ToString("X",CultureInfo.InvariantCulture),NumberStyles.AllowHexSpecifier,CultureInfo.InvariantCulture)==a,"large hexadecimal round trip");
            Require(((a&b)|(a^b))==(a|b),"bitwise decomposition");Require(~a==-a-B.One,"two's-complement complement");
            Require((a<<37)>>37==a,"arithmetic shift round trip");
            B gcd=B.GreatestCommonDivisor(a,b);Require(gcd>=B.Zero && a%gcd==B.Zero && b%gcd==B.Zero,"GCD divisibility");
            B positive=B.Abs(a)+B.One,modulus=B.Abs(b)+2;Require(B.ModPow(positive,13,modulus)==B.Pow(positive,13)%modulus,"modular exponentiation");
        }
        Require(B.Parse("123456789012345678901234567890").ToString(CultureInfo.InvariantCulture)=="123456789012345678901234567890","fixed decimal vector");
        Require(B.Pow(7,80).ToString(CultureInfo.InvariantCulture)=="40536215597144386832065866109016673800875222251012083746192454448001","fixed exponentiation vector");
        Require(B.ModPow(3,100,97)==81,"fixed modular exponentiation vector");
        bool divide=false,format=false,overflow=false;
        try{B unused=B.One/B.Zero;}catch(DivideByZeroException){divide=true;}
        try{B.Parse("not-an-integer",CultureInfo.InvariantCulture);}catch(FormatException){format=true;}
        try{int unused=(int)(B.One<<100);}catch(OverflowException){overflow=true;}
        Require(divide&&format&&overflow,"original localized exception paths");
        var manager=new ResourceManager("FxResources.System.Runtime.Numerics.SR",typeof(B).Assembly);Require(!string.IsNullOrEmpty(manager.GetString("Overflow_Int32",CultureInfo.InvariantCulture)),"original embedded resource lookup");
        C z=new C(2,3),conjugate=C.Conjugate(z);Require(conjugate.Real==2 && conjugate.Imaginary==-3,"complex conjugate");
        Require(z*conjugate==new C(13,0),"complex multiplication");
        C unit=z/z;Require(Math.Abs(unit.Real-1)<1e-12 && Math.Abs(unit.Imaginary)<1e-12,"complex division");
        C square=C.Sqrt(new C(-4,0));Require(Math.Abs(square.Real)<1e-12 && Math.Abs(Math.Abs(square.Imaginary)-2)<1e-12,"complex square root");
        C round=C.Exp(C.Log(z));Require(C.Abs(round-z)<1e-12,"complex exp/log round trip");
        C angle=C.FromPolarCoordinates(2,0.5);Require(Math.Abs(angle.Magnitude-2)<1e-12 && Math.Abs(angle.Phase-0.5)<1e-12,"complex polar conversion");
        Console.WriteLine("PASS actual original source BigInteger/Complex implementation: "+Checks+" arithmetic, large-number, serialization, resource and error checks");
        Require(typeof(object).Assembly.Location.Replace('\\','/').Contains("/shared/Microsoft.NETCore.App/8.0.31/"),"Source NET8 host");
    }
}
