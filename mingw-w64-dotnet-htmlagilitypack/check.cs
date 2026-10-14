using System;
using HtmlAgilityPack;
class Check {static void Main(){var doc=new HtmlDocument();doc.LoadHtml("<html><body><a href='https://example.org'>λ &amp; 🐾</a><div class='target'><b>unclosed");var link=doc.DocumentNode.SelectSingleNode("//a");if(HtmlEntity.DeEntitize(link.InnerText)!="λ & 🐾"||link.GetAttributeValue("href","")!="https://example.org"||doc.DocumentNode.SelectSingleNode("//div[@class='target']/b").InnerText!="unclosed")throw new Exception("HTML parse/XPath/entity recovery");Console.WriteLine("PASS HtmlAgilityPack real parsing, XPath, Unicode and malformed HTML recovery");}}
