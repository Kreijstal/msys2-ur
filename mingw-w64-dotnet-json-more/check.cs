using System;
using System.Text.Json;
using System.Text.Json.Nodes;
using Json.More;

static void Require(bool condition, string message)
{
    if (!condition) throw new Exception(message);
}
using var a = JsonDocument.Parse("{\"a\":1,\"nested\":[true,null,\"value\"]}");
using var b = JsonDocument.Parse("{\"nested\":[true,null,\"value\"],\"a\":1.0}");
Require(a.IsEquivalentTo(b), "Object ordering or numeric equivalence failed");
Require(a.RootElement.GetEquivalenceHashCode() == b.RootElement.GetEquivalenceHashCode(), "Equivalent values have different hashes");
using var different = JsonDocument.Parse("{\"a\":2}");
Require(!a.IsEquivalentTo(different), "Different documents compare equal");
var node = JsonNode.Parse("{\"text\":\"a\\nb\",\"array\":[1,2]}");
Require(node.IsEquivalentTo(JsonNode.Parse(node.AsJsonString())), "JsonNode serialization round-trip failed");
var identity = typeof(JsonElementExtensions).Assembly.GetName();
Require(identity.Version == new Version(2, 0, 0, 0), "Incorrect assembly version");
Require(identity.GetPublicKeyToken().Length == 8, "Signing identity missing");
Console.WriteLine("PASS: Json.More object/numeric equivalence, hashing, negatives and node round-trip");
