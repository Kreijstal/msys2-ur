#pragma warning disable SYSLIB0011
using System;
using System.IO;
using System.Runtime.Serialization.Formatters.Binary;
using ResourceFixtures;
internal static class FixtureGenerator
{
    static void Main(string[] args)
    {
        Directory.CreateDirectory(args[0]);var payload=new Payload();payload.Self=payload;
        foreach(var pair in new (string name,object value)[]{("string","λ serialized 世界"),("array",new[]{1,-2,3}),("class",payload)})
        { using var stream=File.Create(Path.Combine(args[0],pair.name+".nrbf"));new BinaryFormatter().Serialize(stream,pair.value); }
        Console.WriteLine("PASS source NET8 generated3 owned resource NRBF payloads");
    }
}
