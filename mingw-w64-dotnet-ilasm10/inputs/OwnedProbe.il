.assembly extern System.Runtime
{
  .publickeytoken = (B0 3F 5F 7F 11 D5 0A 3A)
  .ver 8:0:0:0
}
.assembly OwnedILAsmProbe { .ver 1:0:0:0 }
.module OwnedILAsmProbe.dll
.class public sealed Program extends [System.Runtime]System.Object
{
  .method public static int32 Main() cil managed
  {
    .entrypoint
    .maxstack 2
    .locals init (int32 sum, int32 current)
    ldc.i4.0
    stloc.0
    ldc.i4.1
    stloc.1
    br.s TEST
  LOOP:
    ldloc.0
    ldloc.1
    add
    stloc.0
    ldloc.1
    ldc.i4.1
    add
    stloc.1
  TEST:
    ldloc.1
    ldc.i4.s 10
    ble.s LOOP
    ldloc.0
    ldc.i4.s 55
    ceq
    ldc.i4.1
    xor
    ret
  }
}
