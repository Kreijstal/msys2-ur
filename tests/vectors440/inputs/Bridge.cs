using System;
using System.Numerics;
public static class Bridge
{
    static void Require(bool condition,string message){if(!condition)throw new Exception(message);}
    static bool Near(float a,float b)=>Math.Abs(a-b)<0.0001f;
    static void Numeric<T>(T value) where T:struct
    {
        var a=new Vector<T>(value);var storage=new T[Vector<T>.Count+2];a.CopyTo(storage,1);
        Require(Vector<T>.Count>0 && storage[1].Equals(value) && storage[Vector<T>.Count].Equals(value),"generic copy and count "+typeof(T));
        var b=new Vector<T>(storage,1);Require(a.Equals(b) && Vector.EqualsAll(a,b),"generic equality "+typeof(T));
        Require(Vector.ConditionalSelect(Vector.Equals(a,b),a,Vector<T>.Zero).Equals(a),"generic condition selection "+typeof(T));
        Require(Vector.BitwiseAnd(a,a).Equals(a) && Vector.BitwiseOr(a,Vector<T>.Zero).Equals(a) && Vector.Xor(a,a).Equals(Vector<T>.Zero),"generic bitwise "+typeof(T));
    }
    public static string Run()
    {
        Require(typeof(Vector<int>).Assembly.GetName().Version.ToString()=="4.1.3.0","exact original generic vector implementation");
        Numeric<byte>(7);Numeric<sbyte>(-7);Numeric<short>(-123);Numeric<ushort>(123);Numeric<int>(12345);Numeric<uint>(12345);Numeric<long>(-123456);Numeric<ulong>(123456);Numeric<float>(1.25f);Numeric<double>(1.25);
        var ints=new Vector<int>(3);Require((ints+ints)[0]==6 && (ints*ints)[0]==9 && (ints-ints).Equals(Vector<int>.Zero),"generic arithmetic");
        Require(Vector.Dot(ints,ints)==9*Vector<int>.Count && Vector.Abs(new Vector<int>(-3)).Equals(ints),"generic dot and abs");
        Require(Vector.Min(ints,new Vector<int>(4)).Equals(ints) && Vector.Max(ints,new Vector<int>(4))[0]==4,"generic min/max");
        Require(Vector.LessThanAll(ints,new Vector<int>(4)) && Vector.GreaterThanAny(ints,Vector<int>.Zero),"generic comparisons");
        var doubles=new Vector<double>(9);Require(Vector.SquareRoot(doubles)[0]==3,"generic square root");
        Require(Vector.ConvertToSingle(new Vector<int>(17))[0]==17 && Vector.ConvertToInt32(new Vector<float>(17.9f))[0]==17,"generic conversions");
        Vector<ushort> lo,hi;Vector.Widen(new Vector<byte>(123),out lo,out hi);Require(lo[0]==123 && hi[0]==123 && Vector.Narrow(lo,hi)[0]==123,"widen/narrow");
        Require(Vector.AsVectorInt32(Vector.AsVectorSingle(ints)).Equals(ints),"generic bit reinterpretation");
        bool negative=false;try{var unused=ints[-1];}catch(IndexOutOfRangeException){negative=true;}Require(negative,"negative vector index");
        negative=false;try{var unused=ints[Vector<int>.Count];}catch(IndexOutOfRangeException){negative=true;}Require(negative,"upper vector index");
        negative=false;try{var unused=new Vector<int>(new int[Vector<int>.Count-1]);}catch(IndexOutOfRangeException){negative=true;}catch(ArgumentException){negative=true;}Require(negative,"short vector input");
        negative=false;try{var unused=Vector<bool>.Count;}catch(NotSupportedException){negative=true;}catch(TypeInitializationException error){negative=error.InnerException is NotSupportedException;}Require(negative,"unsupported generic scalar");
        var a=new Vector2(3,4);Require(Near(a.Length(),5) && Vector2.Dot(a,a)==25,"Vector2 length/dot");
        Require(Vector2.Normalize(a)==new Vector2(0.6f,0.8f),"Vector2 normalize");Require(Vector2.Lerp(Vector2.Zero,a,0.5f)==new Vector2(1.5f,2),"Vector2 lerp");
        var x=new Vector3(1,0,0);var y=new Vector3(0,1,0);Require(Vector3.Cross(x,y)==new Vector3(0,0,1),"cross product");
        Require(Vector3.Reflect(new Vector3(1,-1,0),y)==new Vector3(1,1,0),"reflection");
        var four=new Vector4(1,2,3,4);Require(Vector4.Dot(four,four)==30 && Vector4.Clamp(four,Vector4.Zero,new Vector4(2))==new Vector4(1,2,2,2),"Vector4 arithmetic/clamp");
        var matrix=Matrix3x2.CreateScale(2,3)*Matrix3x2.CreateTranslation(5,7);Require(Vector2.Transform(new Vector2(1,2),matrix)==new Vector2(7,13),"affine order");
        Matrix3x2 inv2;Require(Matrix3x2.Invert(matrix,out inv2),"affine inverse exists");var roundtrip=Vector2.Transform(new Vector2(7,13),inv2);Require(Near(roundtrip.X,1) && Near(roundtrip.Y,2),"affine inverse roundtrip");
        Require(!Matrix3x2.Invert(new Matrix3x2(),out inv2),"singular affine inverse");
        var q=Quaternion.CreateFromAxisAngle(new Vector3(0,0,1),(float)Math.PI/2);var rotated=Vector3.Transform(x,q);Require(Near(rotated.X,0) && Near(rotated.Y,1),"quaternion rotation");
        Require(Quaternion.Multiply(q,Quaternion.Inverse(q)).W>0.9999f,"quaternion inverse");
        var transform=Matrix4x4.CreateScale(2,3,4)*Matrix4x4.CreateFromQuaternion(q)*Matrix4x4.CreateTranslation(5,7,9);Matrix4x4 inverse;Require(Matrix4x4.Invert(transform,out inverse),"4x4 inverse exists");
        var back=Vector3.Transform(Vector3.Transform(new Vector3(1,2,3),transform),inverse);Require(Near(back.X,1) && Near(back.Y,2) && Near(back.Z,3),"4x4 inverse roundtrip");
        Vector3 scale,translation;Quaternion rotation;Require(Matrix4x4.Decompose(transform,out scale,out rotation,out translation) && translation==new Vector3(5,7,9),"matrix decomposition");
        Require(!Matrix4x4.Invert(new Matrix4x4(),out inverse),"singular matrix negative control");
        var plane=Plane.CreateFromVertices(Vector3.Zero,x,y);Require(Near(Math.Abs(plane.Normal.Z),1) && Near(Plane.DotCoordinate(plane,new Vector3(1,2,0)),0),"plane geometry");
        Require(Vector3.TransformNormal(x,Matrix4x4.CreateTranslation(5,7,9))==x,"normal excludes translation");
        return "PASS old generic vectors for ten scalar types, arithmetic/comparison/bitwise/conversion/negative controls and vector/matrix/quaternion/plane geometry";
    }
}
