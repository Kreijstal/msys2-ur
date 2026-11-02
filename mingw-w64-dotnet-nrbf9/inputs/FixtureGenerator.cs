#pragma warning disable SYSLIB0011
using System;
using System.IO;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Formatters.Binary;
using System.Text.Json;
namespace NrbfFixtures
{
    [Serializable]
    public sealed class Payload
    {
        public string Text="λ世界";
        public int Number=-123;
        public bool Flag=true;
        public double Real=1.25;
        public ulong Unsigned=ulong.MaxValue;
        public object? Shared;
        public object? Again;
        public object? Self;
        public int[] Values=new[]{1,-2,3};
        [OnDeserialized] private void Decoded(StreamingContext _) => File.WriteAllText(Environment.GetEnvironmentVariable("NRBF9_SENTINEL")!,"Object deserialized");
    }
    internal static class FixtureGenerator
    {
        static void Main(string[] args)
        {
            Directory.CreateDirectory(args[0]);
            object shared=new object();var value=new Payload{Shared=shared,Again=shared};value.Self=value;
            var data=new (string name,object value)[]{
                ("string","λ世界"),("int",-123),("ulong",ulong.MaxValue),("bool",true),("double",1.25),("decimal",123.5m),
                ("datetime",new DateTime(2025,1,2,3,4,5,DateTimeKind.Utc)),("timespan",TimeSpan.FromTicks(123456789)),
                ("integers",new[]{int.MinValue,-2,0,int.MaxValue}),("strings",new string?[]{"λ",null,"世界",""}),
                ("jagged",new int[][]{new[]{1,2},new[]{3,4}}),("rectangular",new int[,]{{1,2},{3,4}}),
                ("objects",new object?[]{42,"λ世界",null,true}),("class",value)
            };
            foreach(var item in data)
            {
                using var stream=File.Create(Path.Combine(args[0],item.name+".nrbf"));new BinaryFormatter().Serialize(stream,item.value);
            }
            File.WriteAllText(Path.Combine(args[0],"fixture-count.json"),JsonSerializer.Serialize(data.Length));
            Console.WriteLine("PASS source NET8 formatter generated"+data.Length+" owned NRBF fixtures;no deserialization performed");
        }
    }
}
