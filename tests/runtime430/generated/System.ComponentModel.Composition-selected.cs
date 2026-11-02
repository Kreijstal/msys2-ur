namespace System
{
    public partial class Lazy<T, TMetadata> : Lazy<T>
    {
        public Lazy(TMetadata metadata, bool isThreadSafe) { }

        public Lazy(TMetadata metadata, Threading.LazyThreadSafetyMode mode) { }

        public Lazy(TMetadata metadata) { }

        public Lazy(Func<T> valueFactory, TMetadata metadata, bool isThreadSafe) { }

        public Lazy(Func<T> valueFactory, TMetadata metadata, Threading.LazyThreadSafetyMode mode) { }

        public Lazy(Func<T> valueFactory, TMetadata metadata) { }

        public TMetadata Metadata { get { throw null; } }
    }
}