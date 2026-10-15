using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Microsoft.Toolkit.HighPerformance;
using Microsoft.Toolkit.HighPerformance.Buffers;
using Microsoft.Toolkit.HighPerformance.Extensions;
using Microsoft.Toolkit.HighPerformance.Helpers;
struct Square : IRefAction<int> { public void Invoke(ref int x) => x *= x; }
struct AddOne : IRefAction<float> { public void Invoke(ref float x) => x += 1; }
class Check {
static void Assert(bool ok,string what){if(!ok)throw new Exception(what);}
static void Main(){
var asm=typeof(Span2D<int>).Assembly.GetName();
var token=Convert.ToHexString(asm.GetPublicKeyToken()!).ToLowerInvariant();
Assert(asm.Name=="Microsoft.Toolkit.HighPerformance"&&asm.Version==new Version(7,0,0,0)&&token=="4aff67a105548ee2","strong-name identity "+asm.FullName);
// Span2D over a 2D array: indexing, slicing, row/column enumeration (array-layout-dependent fast paths)
var grid=new int[5,7];for(int i=0;i<5;i++)for(int j=0;j<7;j++)grid[i,j]=i*10+j;
Span2D<int> s=grid;Assert(s.Height==5&&s.Width==7&&s[3,4]==34,"Span2D indexing");
var sub=s.Slice(1,2,3,4);Assert(sub.Height==3&&sub.Width==4&&sub[0,0]==12&&sub[2,3]==35,"Span2D slice");
sub.Fill(-1);Assert(grid[1,2]==-1&&grid[3,5]==-1&&grid[0,2]==2&&grid[1,6]==16&&grid[4,5]==45,"Span2D slice fill");
Assert(grid.GetRow(4).ToArray().SequenceEqual(new[]{40,41,42,43,44,45,46}),"GetRow");
Assert(grid.GetColumn(1).ToArray().SequenceEqual(new[]{1,11,21,31,41}),"GetColumn");
Assert(grid.GetRowSpan(0).Length==7&&grid.GetRowSpan(0)[6]==6,"GetRowSpan");
Assert(grid.Count(-1)==12,"2D Count");
var copy=sub.ToArray();Assert(copy.GetLength(0)==3&&copy.GetLength(1)==4&&copy.Cast<int>().All(x=>x==-1),"Span2D ToArray");
// Span2D over a 1D buffer with pitch
var flat=Enumerable.Range(0,20).ToArray();var pitched=new Span2D<int>(flat,1,3,3,2);
Assert(pitched[0,0]==1&&pitched[1,0]==6&&pitched[2,2]==13&&!pitched.TryGetSpan(out _),"Span2D pitch");
// Memory2D + ParallelHelper over it
var m=new Memory2D<float>(new float[64*48],64,48);ParallelHelper.ForEach<float,AddOne>(m);
Assert(m.Span.ToArray().Cast<float>().All(x=>x==1f),"ParallelHelper.ForEach over Memory2D");
var ms=m.Slice(10,10,4,4);ms.Span.Fill(5);Assert(m.Span[13,13]==5&&m.Span[14,14]==1&&ms.Span.Length==16,"Memory2D slice");
var nums=Enumerable.Range(0,1000).ToArray();ParallelHelper.ForEach<int,Square>(nums.AsMemory());
Assert(nums[999]==999*999&&nums[7]==49,"ParallelHelper.ForEach over Memory");
// Buffers
using(var owner=MemoryOwner<byte>.Allocate(100)){owner.Span.Fill(7);var sl=owner.Slice(10,20);Assert(sl.Length==20&&sl.Span[19]==7,"MemoryOwner");}
using(var w=new ArrayPoolBufferWriter<char>()){foreach(var c in "hello, pooled world")w.Write(c);Assert(new string(w.WrittenSpan)=="hello, pooled world","ArrayPoolBufferWriter");}
var pool=new StringPool();var a=pool.GetOrAdd("texture".AsSpan());var b=pool.GetOrAdd(Encoding.UTF8.GetBytes("texture"),Encoding.UTF8);
Assert(ReferenceEquals(a,b)&&pool.TryGet("texture".AsSpan(),out var c2)&&ReferenceEquals(a,c2),"StringPool");
// Helpers / NET5_0-only extensions
Assert(BitHelper.ExtractRange(0b1011_0110u,2,4)==0b1101u&&BitHelper.HasFlag(0x80u,7)&&!BitHelper.HasFlag(0x80u,6),"BitHelper");
Assert(HashCode<int>.Combine(new[]{1,2,3})==HashCode<int>.Combine(new[]{1,2,3})&&HashCode<int>.Combine(new[]{1,2,3})!=HashCode<int>.Combine(new[]{3,2,1}),"HashCode<T>");
var list=new List<int>{1,2,3};list.AsSpan()[1]=42;Assert(list[1]==42,"List<T>.AsSpan (NET5_0 path)");
int? n=5;n.DangerousGetValueOrDefaultReference()=9;Assert(n==9,"Nullable ref (NET5_0 path)");
var boxed=(object)123;Assert(Box<int>.TryGetFrom(boxed,out var box)&&box!.GetReference()==123,"Box<T>");
Console.WriteLine("PASS Microsoft.Toolkit.HighPerformance "+asm.Version+" strong-named token "+token+"; Span2D index/slice/fill/pitch/rows/columns, Memory2D slice, ParallelHelper, MemoryOwner, ArrayPoolBufferWriter, StringPool, BitHelper, HashCode<T>, List.AsSpan, Nullable ref, Box<T>");}}
