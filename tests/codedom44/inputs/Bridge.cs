using System;
using System.CodeDom;
using System.CodeDom.Compiler;
using System.IO;
using System.Reflection;
using Microsoft.CSharp;
using Microsoft.VisualBasic;

public static class Bridge
{
    static void Require(bool value, string message) { if (!value) throw new Exception(message); }
    public static string Run(string directory)
    {
        var unit = new CodeCompileUnit();
        var space = new CodeNamespace("PortProof");
        unit.Namespaces.Add(space);
        var type = new CodeTypeDeclaration("Program") { TypeAttributes = TypeAttributes.Public };
        space.Types.Add(type);
        var method = new CodeMemberMethod { Name = "event", ReturnType = new CodeTypeReference(typeof(int)), Attributes = MemberAttributes.Public | MemberAttributes.Static };
        method.Statements.Add(new CodeMethodReturnStatement(new CodeBinaryOperatorExpression(new CodePrimitiveExpression(40), CodeBinaryOperatorType.Add, new CodePrimitiveExpression(2))));
        type.Members.Add(method);
        var main = new CodeEntryPointMethod();
        main.Statements.Add(new CodeExpressionStatement(new CodeMethodInvokeExpression(new CodeTypeReferenceExpression(typeof(Console)), "WriteLine", new CodeMethodInvokeExpression(new CodeTypeReferenceExpression("Program"), "event"))));
        main.Statements.Add(new CodeExpressionStatement(new CodeMethodInvokeExpression(new CodeTypeReferenceExpression(typeof(Console)), "WriteLine", new CodePrimitiveExpression("héllo Ω \"quoted\"\nsecond"))));
        type.Members.Add(main);
        CodeGenerator.ValidateIdentifiers(unit);
        unit.UserData["proof"] = 42;
        Require((int)unit.UserData["proof"] == 42 && type.Members.Count == 2, "CodeDOM collections and user data");
        using (var cs = new CSharpCodeProvider())
        using (var vb = new VBCodeProvider())
        {
            Require(cs.FileExtension == "cs" && vb.FileExtension == "vb", "provider extensions");
            Require(cs.CreateEscapedIdentifier("class") == "@class", "CSharp keyword escaping");
            Require(vb.CreateEscapedIdentifier("Class") == "[Class]", "VB keyword escaping");
            Require(cs.IsValidIdentifier("hello_42") && !cs.IsValidIdentifier("bad name"), "identifier validation");
            foreach (var provider in new CodeDomProvider[] { cs, vb })
            {
                var writer = new StringWriter();
                provider.GenerateCodeFromCompileUnit(unit, writer, new CodeGeneratorOptions { IndentString = "  ", BracingStyle = "C" });
                string code = writer.ToString();
                Require(code.Contains("PortProof") && code.Contains("Program"), "generated source");
                File.WriteAllText(Path.Combine(directory, "Generated." + provider.FileExtension), code);
                bool unsupported = false;
                try { provider.CompileAssemblyFromSource(new CompilerParameters(), "invalid source"); }
                catch (PlatformNotSupportedException) { unsupported = true; }
                Require(unsupported, "original NS2 in-process compiler unsupported path");
            }
        }
        using (var provider = CodeDomProvider.CreateProvider("CSharp"))
            Require(provider.GetType() == typeof(CSharpCodeProvider), "provider registry");
        var invalid = new CodeCompileUnit();
        invalid.Namespaces.Add(new CodeNamespace("bad namespace"));
        bool rejected = false;
        try { CodeGenerator.ValidateIdentifiers(invalid); } catch (ArgumentException) { rejected = true; }
        Require(rejected, "invalid code tree rejected");
        var errors = new CompilerErrorCollection();
        errors.Add(new CompilerError("sample.cs", 3, 4, "E1", "failure"));
        errors.Add(new CompilerError("sample.cs", 5, 6, "W1", "warning") { IsWarning = true });
        Require(errors.HasErrors && errors.HasWarnings && errors[0].Line == 3, "compiler diagnostic model");
        using (var temp = new TempFileCollection(directory, false))
        {
            var name = temp.AddExtension("porttest");
            File.WriteAllText(name, "owned temporary data");
            Require(File.Exists(name), "temporary file creation");
            temp.Delete();
            Require(!File.Exists(name), "temporary file deletion");
        }
        return "PASS original CodeDom model, CSharp/VB providers, keyword/Unicode generation, validation, unsupported compiler paths and temporary-file ownership";
    }
}
