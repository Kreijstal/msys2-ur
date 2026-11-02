using System;
using System.Numerics;
using System.Text;
class Program
{
    static void Require(bool value,string text){if(!value)throw new Exception(text);}
    static int Main()
    {
        var text=new StringBuilder("source");Require(text[0]=='s',"original Chars getter");text[0]='S';Require(text.ToString()=="Source" && "source"[2]=='u',"original Chars setters/getters");
        var huge=BigInteger.Pow(new BigInteger(7),50);Require(BigInteger.Parse(huge.ToString())==huge && huge>long.MaxValue,"BigInteger original contract");
        var complex=new Complex(2,3)*new Complex(2,-3);Require(complex.Real==13 && complex.Imaginary==0,"Complex original contract");
        var point=Vector3.Transform(new Vector3(1,2,3),Matrix4x4.CreateTranslation(4,5,6));Require(point==new Vector3(5,7,9),"source runtime vector/matrix consumer");
        var q=Quaternion.Identity;Require(Vector2.Transform(new Vector2(2,3),q)==new Vector2(2,3),"quaternion/vector contract");
        foreach(var type in new[]{typeof(object),typeof(BigInteger),typeof(Vector3)})Require(type.Assembly.Location.Replace('\\','/').Contains("/shared/Microsoft.NETCore.App/8.0.31/"),"source runtime implementation location");
        Console.WriteLine("PASS original NET46 source-contract typed consumer: Chars indexers, BigInteger, Complex, vectors/matrix/quaternion on source NET8 host");return 0;
    }
}
