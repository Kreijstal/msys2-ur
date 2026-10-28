using System;
using System.Globalization;
using Humanizer;

static void Require(bool condition, string message)
{
    if (!condition) throw new Exception(message);
}
CultureInfo.CurrentCulture = CultureInfo.GetCultureInfo("en-US");
CultureInfo.CurrentUICulture = CultureInfo.GetCultureInfo("en-US");
Require("SomePropertyName".Underscore() == "some_property_name", "Snake-case conversion failed");
Require("person".Pluralize() == "people", "Irregular pluralization failed");
Require("people".Singularize() == "person", "Singularization failed");
Require("SomePropertyName".Humanize() == "Some property name", "Humanized label incorrect");
Require(42.ToWords() == "forty-two", "Number formatting failed");
Require(TimeSpan.FromMinutes(2).Humanize() == "2 minutes", "Embedded neutral resources missing");
var identity = typeof(StringHumanizeExtensions).Assembly.GetName();
Require(identity.Version == new Version(2, 14, 0, 0), "Incorrect assembly version");
Require(identity.GetPublicKeyToken().Length == 8, "Signing identity missing");
Console.WriteLine("PASS: Humanizer casing, inflection, words, resources and signing identity");
