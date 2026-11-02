using System;
using System.Text.Json;
using Json.Pointer;

static void Require(bool condition, string message)
{
    if (!condition) throw new Exception(message);
}
using var document = JsonDocument.Parse("{\"a/b\":{\"~key\":[\"zero\",\"one\"]}}");
var pointer = JsonPointer.Parse("/a~1b/~0key/1");
Require(pointer.Evaluate(document.RootElement)?.GetString() == "one", "Escaped property/array evaluation failed");
Require(JsonPointer.Parse("").Evaluate(document.RootElement)?.ValueKind == JsonValueKind.Object, "Root pointer failed");
Require(JsonPointer.Parse("/missing").Evaluate(document.RootElement) == null, "Missing member did not return null");
Require(!JsonPointer.TryParse("invalid", out _), "Invalid pointer accepted");
var options = new PointerCreationOptions { PropertyNameResolver = PropertyNameResolvers.SnakeCase };
var created = JsonPointer.Create<Model>(model => model.SomePropertyName, options);
Require(created.ToString() == "/some_property_name", "Humanizer-backed property naming failed");
Require(JsonSerializer.Deserialize<JsonPointer>(JsonSerializer.Serialize(pointer)).ToString() == pointer.ToString(), "Pointer JSON round-trip failed");
var identity = typeof(JsonPointer).Assembly.GetName();
Require(identity.Version == new Version(5, 0, 0, 0), "Incorrect assembly version");
Require(identity.GetPublicKeyToken().Length == 8, "Signing identity missing");
Console.WriteLine("PASS: JsonPointer escaping, arrays, missing paths, invalid input, Humanizer and JSON round-trip");
public sealed class Model { public string SomePropertyName { get; set; } = "value"; }
