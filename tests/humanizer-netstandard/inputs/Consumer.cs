using System;
using System.Globalization;
using Humanizer;

public static class StandardHumanizerConsumer
{
    static void Require(bool ok,string message){if(!ok)throw new Exception(message);}
    public static string Run()
    {
        CultureInfo.CurrentCulture=CultureInfo.GetCultureInfo("en-US");
        CultureInfo.CurrentUICulture=CultureInfo.GetCultureInfo("en-US");
        Require("SomePropertyName".Underscore()=="some_property_name","underscore conversion");
        Require("SomePropertyName".Humanize()=="Some property name","humanized label");
        Require("person".Pluralize()=="people" && "people".Singularize()=="person","irregular inflection");
        Require(42.ToWords()=="forty-two","English number words");
        Require(42.ToWords(CultureInfo.GetCultureInfo("de-DE"))=="zweiundvierzig","German number words");
        Require(TimeSpan.FromMinutes(2).Humanize()=="2 minutes","neutral resource formatting");
        Require(21.Ordinalize()=="21st","ordinal formatting");
        return "PASS original netstandard2.0 Humanizer casing, irregular inflection, English/German numbers, resources and ordinals";
    }
}
