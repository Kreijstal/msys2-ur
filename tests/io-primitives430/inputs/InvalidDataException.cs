namespace System.IO
{
    [global::System.Serializable]
    public sealed partial class InvalidDataException : SystemException
    {
        public InvalidDataException() { }

        internal InvalidDataException(Runtime.Serialization.SerializationInfo info, Runtime.Serialization.StreamingContext context) { }

        public InvalidDataException(string message, Exception innerException) { }

        public InvalidDataException(string message) { }
    }
}