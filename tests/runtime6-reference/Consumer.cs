using System;
using System.Collections.Generic;
using System.Formats.Asn1;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;

internal static class Program
{
    static int Main()
    {
        if (DateOnly.Parse("2023-06-18").ToString("yyyy-MM-dd") != "2023-06-18") throw new Exception("NET6 DateOnly");
        var writer = new AsnWriter(AsnEncodingRules.DER);
        writer.WriteInteger(12345);
        var reader = new AsnReader(writer.Encode(), AsnEncodingRules.DER);
        if (reader.ReadInteger() != 12345 || reader.HasData) throw new Exception("NET6 ASN.1 contract");
        var data = new Dictionary<string, int> { ["Grüße 世界"] = 42 };
        var roundTrip = JsonSerializer.Deserialize<Dictionary<string, int>>(JsonSerializer.Serialize(data));
        if (roundTrip!["Grüße 世界"] != 42 || Enumerable.Range(1, 5).Sum() != 15) throw new Exception("NET6 JSON/LINQ contract");
        byte[] random = new byte[32];
        RandomNumberGenerator.Fill(random);
        if (SHA256.HashData(random).Length != 32) throw new Exception("NET6 crypto contract");
        Console.WriteLine("PASS consumer compiled only with produced NET6 core references: DateOnly, ASN.1, Unicode JSON/LINQ and crypto; executed on source NET8 host");
        return 0;
    }
}
