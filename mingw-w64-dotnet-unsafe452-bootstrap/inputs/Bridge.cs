using System;
using System.Runtime.CompilerServices;
public static class Bridge
{
    static void Require(bool condition,string message){if(!condition)throw new Exception(message);}
    struct Pair{public int Left;public int Right; public Pair(int left,int right){Left=left;Right=right;}}
    public static unsafe string Run()
    {
        Require(typeof(Unsafe).Assembly.GetName().Version.ToString()=="4.0.4.1","exact Unsafe4.5.2 identity");
        Require(Unsafe.SizeOf<int>()==4 && Unsafe.SizeOf<Pair>()==8,"generic sizes");
        object text="owned";Require(Unsafe.As<string>(text)=="owned","object retyping");
        int value=0x3f800000;Require(Unsafe.As<int,float>(ref value)==1.0f,"generic bit reinterpretation");
        void* pointer=Unsafe.AsPointer(ref value);Require(Unsafe.AreSame(ref value,ref Unsafe.AsRef<int>(pointer)),"pointer/reference identity");
        Require(Unsafe.AreSame(ref value,ref Unsafe.AsRef(in value)),"readonly reference identity");
        int[] values={10,20,30,40};
        fixed(int* first=values)
        {
            ref int start=ref values[0];ref int second=ref Unsafe.Add(ref start,1);
            Require(second==20 && Unsafe.Add(ref start,new IntPtr(2))==30,"typed element addition");
            Require(*(int*)Unsafe.Add<int>(first,3)==40,"pointer element addition");
            Require(Unsafe.Subtract(ref second,1)==10 && Unsafe.Subtract(ref second,new IntPtr(1))==10,"typed subtraction");
            Require(*(int*)Unsafe.Subtract<int>(first+2,2)==10,"pointer subtraction");
            Require(Unsafe.AddByteOffset(ref start,new IntPtr(4))==20 && Unsafe.SubtractByteOffset(ref second,new IntPtr(4))==10,"byte-offset references");
            Require(Unsafe.ByteOffset(ref start,ref second)==new IntPtr(4),"reference distance");
            Require(Unsafe.IsAddressGreaterThan(ref second,ref start) && Unsafe.IsAddressLessThan(ref start,ref second),"address ordering");
            Require(!Unsafe.AreSame(ref start,ref second),"distinct-reference negative control");
        }
        byte* memory=stackalloc byte[80];byte* other=stackalloc byte[80];
        Unsafe.InitBlock(memory,0x11,80);Require(memory[0]==0x11 && memory[79]==0x11,"pointer block initialization");
        Unsafe.InitBlock(ref memory[0],0x22,80);Require(memory[79]==0x22,"reference block initialization");
        Unsafe.InitBlockUnaligned(memory+1,0x33,5);Require(memory[0]==0x22 && memory[1]==0x33 && memory[6]==0x22,"unaligned pointer initialization guards");
        Unsafe.InitBlockUnaligned(ref memory[2],0x44,2);Require(memory[1]==0x33 && memory[2]==0x44 && memory[4]==0x33,"unaligned reference initialization guards");
        Unsafe.Write<int>(memory,123456);Require(Unsafe.Read<int>(memory)==123456,"aligned generic read/write");
        Unsafe.WriteUnaligned<int>(memory+1,7654321);Require(Unsafe.ReadUnaligned<int>(memory+1)==7654321,"unaligned pointer read/write");
        Unsafe.WriteUnaligned<int>(ref memory[3],-9876);Require(Unsafe.ReadUnaligned<int>(ref memory[3])==-9876,"unaligned reference read/write");
        int source=42;Unsafe.Copy<int>(other,ref source);Require(Unsafe.Read<int>(other)==42,"generic copy to pointer");
        int destination=0;Unsafe.Copy<int>(ref destination,other);Require(destination==42,"generic copy from pointer");
        Unsafe.InitBlock(memory,0x5a,80);Unsafe.InitBlock(other,0,80);
        Unsafe.CopyBlock(other,memory,20);Require(other[19]==0x5a && other[20]==0,"pointer block copy guards");
        Unsafe.CopyBlock(ref other[20],ref memory[0],20);Require(other[39]==0x5a && other[40]==0,"reference block copy guards");
        Unsafe.CopyBlockUnaligned(other+41,memory+1,5);Require(other[40]==0 && other[41]==0x5a && other[46]==0,"unaligned pointer block copy");
        Unsafe.CopyBlockUnaligned(ref other[47],ref memory[3],5);Require(other[46]==0 && other[51]==0x5a && other[52]==0,"unaligned reference block copy");
        Unsafe.InitBlockUnaligned(other+52,0xff,0);Unsafe.CopyBlockUnaligned(other+52,memory+1,0);Require(other[52]==0,"zero-length operation controls");
        return "PASS all 34 original Unsafe methods: generic/reference/pointer aliasing, offsets, aligned/unaligned read-write-copy-init and guard controls";
    }
}
