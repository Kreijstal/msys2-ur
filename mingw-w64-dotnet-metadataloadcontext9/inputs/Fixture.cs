using System;
using System.IO;
using System.Runtime.CompilerServices;
[assembly:System.Runtime.Versioning.TargetFramework(".NETCoreApp,Version=v9.0")]
namespace Fixtures
{
    internal static class Guard
    {
        [ModuleInitializer] internal static void Init() => Touch();
        internal static void Touch() => File.WriteAllText(Environment.GetEnvironmentVariable("MLC9_SENTINEL")!,"Fixture executed");
    }
    [AttributeUsage(AttributeTargets.Class)]
    public sealed class TagAttribute : Attribute
    {
        public string Value { get; }
        public TagAttribute(string value) { Guard.Touch(); Value=value; }
    }
    [Tag("λ世界")]
    public class Sample : IDisposable
    {
        public const string Text="λ世界";
        public static int Answer() => 42;
        public int Optional(int value=7) => value;
        public T Echo<T>(T value) => value;
        public ref int ReturnRef(ref int value) => ref value;
        public void Dispose() { }
    }
    public class Plain { public Plain() { } }
    public class GenericBox<T> where T:class,new() { public T Item {get;set;} = new T(); }
}
