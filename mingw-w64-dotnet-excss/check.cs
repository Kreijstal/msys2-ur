using System;
using System.Linq;
using ExCSS;
class Check {static void Main(){var parser=new StylesheetParser();var sheet=parser.Parse(".target { color: red; font-weight: bold } @media screen { .nested { display: block } }");var rule=(StyleRule)sheet.StyleRules.Single();if(rule.SelectorText!=".target"||rule.Style.Color!="rgb(255, 0, 0)"||rule.Style.FontWeight!="bold"||sheet.MediaRules.Count()!=1)throw new Exception("CSS parser, declarations and nested media rule");var recovered=(StyleRule)parser.Parse("h1 {color:red; font-weight:bold").StyleRules.Single();if(recovered.Style.FontWeight!="bold")throw new Exception("CSS EOF recovery");Console.WriteLine("PASS ExCSS selectors, declarations, nested media and incomplete stylesheet recovery");}}
