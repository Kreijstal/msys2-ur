using System;
using System.Text.Json.Nodes;
using Json.Schema;

static void Require(bool condition, string message)
{
    if (!condition) throw new Exception(message);
}
var schema = JsonSchema.FromText("""
{
  "$schema":"https://json-schema.org/draft/2020-12/schema",
  "$defs":{"identifier":{"type":"integer","minimum":1}},
  "type":"object",
  "properties":{"id":{"$ref":"#/$defs/identifier"},"names":{"type":"array","items":{"type":"string"},"minItems":1}},
  "required":["id","names"],
  "additionalProperties":false
}
""");
var options = new EvaluationOptions { OutputFormat = OutputFormat.List };
Require(schema.Evaluate(JsonNode.Parse("{\"id\":2,\"names\":[\"one\"]}"), options).IsValid, "Valid instance rejected");
foreach (var invalid in new[] {
    "{\"id\":0,\"names\":[\"one\"]}",
    "{\"id\":2,\"names\":[5]}",
    "{\"id\":2}",
    "{\"id\":2,\"names\":[],\"extra\":true}",
}) Require(!schema.Evaluate(JsonNode.Parse(invalid), options).IsValid, "Invalid instance accepted: " + invalid);
var identity = typeof(JsonSchema).Assembly.GetName();
Require(identity.Version == new Version(7, 0, 0, 0), "Incorrect assembly version");
Require(identity.GetPublicKeyToken().Length == 8, "Signing identity missing");
Console.WriteLine("PASS: JsonSchema 2020-12 local refs, types, ranges, arrays, required and additional properties");
