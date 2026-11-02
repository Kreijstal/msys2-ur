using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Primitives;

public sealed class Settings
{
    public string Name { get; set; }="";
    public int Count { get; set; }
    public bool Enabled { get; set; }
    public int[] Numbers { get; set; }=Array.Empty<int>();
    public Nested Nested { get; set; }=new();
}
public sealed class Nested { public string Label { get; set; }=""; }
internal static class Program
{
    static void Require(bool value,string message) { if(!value)throw new Exception(message); }
    static void CheckInterceptedIL()
    {
        var codes=typeof(OpCodes).GetFields(BindingFlags.Public|BindingFlags.Static).Where(f=>f.FieldType==typeof(OpCode)).Select(f=>(OpCode)f.GetValue(null)!).ToDictionary(c=>unchecked((ushort)c.Value));
        var method=typeof(Program).GetMethod(nameof(Main),BindingFlags.Static|BindingFlags.Public)!;
        var il=method.GetMethodBody()!.GetILAsByteArray()!;bool found=false;
        for(int i=0;i<il.Length;)
        {
            ushort value=il[i++];if(value==0xfe)value=(ushort)(0xfe00|il[i++]);var code=codes[value];
            if(code.OperandType==OperandType.InlineMethod)
            {
                var called=method.Module.ResolveMethod(BitConverter.ToInt32(il,i));
                if(called?.DeclaringType?.Namespace=="Microsoft.Extensions.Configuration.Binder.SourceGeneration")found=true;
            }
            i+=code.OperandType switch {
                OperandType.InlineNone=>0,
                OperandType.ShortInlineBrTarget or OperandType.ShortInlineI or OperandType.ShortInlineVar=>1,
                OperandType.InlineVar=>2,
                OperandType.InlineI8 or OperandType.InlineR=>8,
                OperandType.InlineSwitch=>4+4*BitConverter.ToInt32(il,i),
                _=>4
            };
        }
        Require(found,"Consumer IL must call the original generator's interceptors");
    }
    public static int Main()
    {
        var config=new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string,string?> {
            ["Name"]="世界",["Count"]="37",["Enabled"]="true",["Numbers:0"]="2",["Numbers:1"]="3",["Nested:Label"]="owned"
        }).Build();
        using var ownedRoot=(IDisposable)config;
        var settings=config.Get<Settings>()!;
        Require(settings.Name=="世界" && settings.Count==37 && settings.Enabled,"Generated scalar binding");
        Require(settings.Numbers.SequenceEqual(new[]{2,3}) && settings.Nested.Label=="owned","Generated array/nested binding");
        int callbacks=0;
        using var registration=ChangeToken.OnChange(config.GetReloadToken,()=>callbacks++);
        config["Count"]="45";config.Reload();Require(callbacks==1,"Configuration reload token");
        Require(config.GetValue<int>("Count")==45,"Generated GetValue after reload");
        var bound=new Settings();config.Bind(bound);Require(bound.Count==45 && bound.Name=="世界","Generated Bind instance");
        config["Count"]="invalid";bool failed=false;
        try { config.GetValue<int>("Count"); } catch(InvalidOperationException) { failed=true; }
        Require(failed,"Invalid integer binding must fail");
        CheckInterceptedIL();
        Console.WriteLine("PASS original NET10 memory configuration/reload and NS2 Roslyn4.8-generated binding for Unicode/scalars/arrays/nested values/errors; emitted IL calls original interceptors");return 0;
    }
}
