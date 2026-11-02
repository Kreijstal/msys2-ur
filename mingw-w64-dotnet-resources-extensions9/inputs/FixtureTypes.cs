#pragma warning disable SYSLIB0050
using System;
using System.Runtime.Serialization;
namespace ResourceFixtures
{
    [Serializable]
    public sealed class Payload : IDeserializationCallback
    {
        public int Number=42;
        public string Text="λ世界";
        public Payload? Self;
        public static int Constructors;
        public static int Events;
        public static int Callbacks;
        public Payload() { Constructors++; }
        [OnDeserialized] private void Deserialized(StreamingContext _) { Events++; }
        public void OnDeserialization(object? sender) { Callbacks++; }
    }
}
