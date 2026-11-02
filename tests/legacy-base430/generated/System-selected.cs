[assembly: System.Runtime.CompilerServices.TypeForwardedTo(typeof(System.Threading.SemaphoreFullException))]
namespace System
{
    [ComponentModel.TypeConverter(typeof(UriTypeConverter))]
    public partial class Uri : Runtime.Serialization.ISerializable
    {
        internal const char c_DummyChar = '\uffff';
        internal const char c_EOL = '\ufffe';
        internal const int c_MaxUriBufferSize = 65520;
        internal static readonly char[] HexLowerChars;
        public static readonly string SchemeDelimiter;
        public static readonly string UriSchemeFile;
        public static readonly string UriSchemeFtp;
        public static readonly string UriSchemeGopher;
        public static readonly string UriSchemeHttp;
        public static readonly string UriSchemeHttps;
        public static readonly string UriSchemeMailto;
        public static readonly string UriSchemeNetPipe;
        public static readonly string UriSchemeNetTcp;
        public static readonly string UriSchemeNews;
        public static readonly string UriSchemeNntp;
        internal static readonly string UriSchemeWs;
        internal static readonly string UriSchemeWss;
        protected Uri(Runtime.Serialization.SerializationInfo serializationInfo, Runtime.Serialization.StreamingContext streamingContext) { }

        [Obsolete("The constructor has been deprecated. Please use new Uri(string). The dontEscape parameter is deprecated and is always false. http://go.microsoft.com/fwlink/?linkid=14202")]
        public Uri(string uriString, bool dontEscape) { }

        public Uri(string uriString, UriKind uriKind) { }

        public Uri(string uriString) { }

        [Obsolete("The constructor has been deprecated. Please new Uri(Uri, string). The dontEscape parameter is deprecated and is always false. http://go.microsoft.com/fwlink/?linkid=14202")]
        public Uri(Uri baseUri, string relativeUri, bool dontEscape) { }

        public Uri(Uri baseUri, string relativeUri) { }

        public Uri(Uri baseUri, Uri relativeUri) { }

        public string AbsolutePath { get { throw null; } }

        public string AbsoluteUri { get { throw null; } }

        public string Authority { get { throw null; } }

        public string DnsSafeHost { get { throw null; } }

        public string Fragment { get { throw null; } }

        internal bool HasAuthority { get { throw null; } }

        public string Host { get { throw null; } }

        public UriHostNameType HostNameType { get { throw null; } }

        public string IdnHost { get { throw null; } }

        public bool IsAbsoluteUri { get { throw null; } }

        public bool IsDefaultPort { get { throw null; } }

        public bool IsFile { get { throw null; } }

        public bool IsLoopback { get { throw null; } }

        public bool IsUnc { get { throw null; } }

        public string LocalPath { get { throw null; } }

        public string OriginalString { get { throw null; } }

        public string PathAndQuery { get { throw null; } }

        public int Port { get { throw null; } }

        public string Query { get { throw null; } }

        public string Scheme { get { throw null; } }

        public string[] Segments { get { throw null; } }

        internal bool UserDrivenParsing { get { throw null; } }

        public bool UserEscaped { get { throw null; } }

        public string UserInfo { get { throw null; } }

        internal static int CalculateCaseInsensitiveHashCode(string text) { throw null; }

        [Obsolete("The method has been deprecated. It is not used by the system. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected virtual void Canonicalize() { }

        public static UriHostNameType CheckHostName(string name) { throw null; }

        public static bool CheckSchemeName(string schemeName) { throw null; }

        [Obsolete("The method has been deprecated. It is not used by the system. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected virtual void CheckSecurity() { }

        public static int Compare(Uri uri1, Uri uri2, UriComponents partsToCompare, UriFormat compareFormat, StringComparison comparisonType) { throw null; }

        internal static Uri CreateHelper(string uriString, bool dontEscape, UriKind uriKind, ref UriFormatException e) { throw null; }

        public override bool Equals(object comparand) { throw null; }

        [Obsolete("The method has been deprecated. It is not used by the system. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected virtual void Escape() { }

        public static string EscapeDataString(string stringToEscape) { throw null; }

        [Obsolete("The method has been deprecated. Please use GetComponents() or static EscapeUriString() to escape a Uri component or a string. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected static string EscapeString(string str) { throw null; }

        internal string EscapeUnescapeIri(string input, int start, int end, UriComponents component) { throw null; }

        public static string EscapeUriString(string stringToEscape) { throw null; }

        public static int FromHex(char digit) { throw null; }

        public string GetComponents(UriComponents components, UriFormat format) { throw null; }

        internal string GetComponentsHelper(UriComponents uriComponents, UriFormat uriFormat) { throw null; }

        public override int GetHashCode() { throw null; }

        public string GetLeftPart(UriPartial part) { throw null; }

        protected void GetObjectData(Runtime.Serialization.SerializationInfo serializationInfo, Runtime.Serialization.StreamingContext streamingContext) { }

        internal string GetParts(UriComponents uriParts, UriFormat formatAs) { throw null; }

        public static string HexEscape(char character) { throw null; }

        public static char HexUnescape(string pattern, ref int index) { throw null; }

        internal static string InternalEscapeString(string rawString) { throw null; }

        internal bool InternalIsWellFormedOriginalString() { throw null; }

        internal static bool IriParsingStatic(UriParser syntax) { throw null; }

        internal static bool IsAsciiLetterOrDigit(char character) { throw null; }

        [Obsolete("The method has been deprecated. It is not used by the system. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected virtual bool IsBadFileSystemCharacter(char character) { throw null; }

        public bool IsBaseOf(Uri uri) { throw null; }

        internal bool IsBaseOfHelper(Uri uriLink) { throw null; }

        internal static bool IsBidiControlCharacter(char ch) { throw null; }

        [Obsolete("The method has been deprecated. It is not used by the system. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected static bool IsExcludedCharacter(char character) { throw null; }

        internal static bool IsGenDelim(char ch) { throw null; }

        public static bool IsHexDigit(char character) { throw null; }

        public static bool IsHexEncoding(string pattern, int index) { throw null; }

        [Obsolete("The method has been deprecated. It is not used by the system. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected virtual bool IsReservedCharacter(char character) { throw null; }

        public bool IsWellFormedOriginalString() { throw null; }

        public static bool IsWellFormedUriString(string uriString, UriKind uriKind) { throw null; }

        [Obsolete("The method has been deprecated. Please use MakeRelativeUri(Uri uri). http://go.microsoft.com/fwlink/?linkid=14202")]
        public string MakeRelative(Uri toUri) { throw null; }

        public Uri MakeRelativeUri(Uri uri) { throw null; }

        public static bool operator ==(Uri uri1, Uri uri2) { throw null; }

        public static bool operator !=(Uri uri1, Uri uri2) { throw null; }

        [Obsolete("The method has been deprecated. It is not used by the system. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected virtual void Parse() { }

        internal UriFormatException ParseMinimal() { throw null; }

        internal static Uri ResolveHelper(Uri baseUri, Uri relativeUri, ref string newUriString, ref bool userEscaped, out UriFormatException e) { throw null; }

        internal static unsafe string StripBidiControlCharacter(char* strToClean, int start, int length) { throw null; }

        void Runtime.Serialization.ISerializable.GetObjectData(Runtime.Serialization.SerializationInfo serializationInfo, Runtime.Serialization.StreamingContext streamingContext) { }

        public override string ToString() { throw null; }

        public static bool TryCreate(string uriString, UriKind uriKind, out Uri result) { throw null; }

        public static bool TryCreate(Uri baseUri, string relativeUri, out Uri result) { throw null; }

        public static bool TryCreate(Uri baseUri, Uri relativeUri, out Uri result) { throw null; }

        [Obsolete("The method has been deprecated. Please use GetComponents() or static UnescapeDataString() to unescape a Uri component or a string. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected virtual string Unescape(string path) { throw null; }

        public static string UnescapeDataString(string stringToUnescape) { throw null; }
    }

    [Flags]
    public enum UriComponents
    {
        SerializationInfoString = int.MinValue,
        Scheme = 1,
        UserInfo = 2,
        Host = 4,
        Port = 8,
        SchemeAndServer = 13,
        Path = 16,
        Query = 32,
        PathAndQuery = 48,
        HttpRequestUrl = 61,
        Fragment = 64,
        AbsoluteUri = 127,
        StrongPort = 128,
        HostAndPort = 132,
        StrongAuthority = 134,
        NormalizedHost = 256,
        KeepDelimiter = 1073741824
    }

    public enum UriFormat
    {
        UriEscaped = 1,
        Unescaped = 2,
        SafeUnescaped = 3
    }

    public partial class UriFormatException : FormatException, Runtime.Serialization.ISerializable
    {
        public UriFormatException() { }

        protected UriFormatException(Runtime.Serialization.SerializationInfo serializationInfo, Runtime.Serialization.StreamingContext streamingContext) { }

        public UriFormatException(string textString, Exception e) { }

        public UriFormatException(string textString) { }

        void Runtime.Serialization.ISerializable.GetObjectData(Runtime.Serialization.SerializationInfo serializationInfo, Runtime.Serialization.StreamingContext streamingContext) { }
    }

    public enum UriHostNameType
    {
        Unknown = 0,
        Basic = 1,
        Dns = 2,
        IPv4 = 3,
        IPv6 = 4
    }

    public enum UriKind
    {
        RelativeOrAbsolute = 0,
        Absolute = 1,
        Relative = 2
    }
}

namespace System.Collections.Generic
{
    public partial interface ISet<T> : ICollection<T>, IEnumerable<T>, IEnumerable
    {
        bool Add(T item);
        void ExceptWith(IEnumerable<T> other);
        void IntersectWith(IEnumerable<T> other);
        bool IsProperSubsetOf(IEnumerable<T> other);
        bool IsProperSupersetOf(IEnumerable<T> other);
        bool IsSubsetOf(IEnumerable<T> other);
        bool IsSupersetOf(IEnumerable<T> other);
        bool Overlaps(IEnumerable<T> other);
        bool SetEquals(IEnumerable<T> other);
        void SymmetricExceptWith(IEnumerable<T> other);
        void UnionWith(IEnumerable<T> other);
    }
}

namespace System.ComponentModel
{
    [AttributeUsage(AttributeTargets.All)]
    public partial class DefaultValueAttribute : Attribute
    {
        public DefaultValueAttribute(bool value) { }

        public DefaultValueAttribute(byte value) { }

        public DefaultValueAttribute(char value) { }

        public DefaultValueAttribute(double value) { }

        public DefaultValueAttribute(short value) { }

        public DefaultValueAttribute(int value) { }

        public DefaultValueAttribute(long value) { }

        public DefaultValueAttribute(object value) { }

        public DefaultValueAttribute(float value) { }

        public DefaultValueAttribute(string value) { }

        public DefaultValueAttribute(Type type, string value) { }

        public virtual object Value { get { throw null; } }

        public override bool Equals(object obj) { throw null; }

        public override int GetHashCode() { throw null; }

        protected void SetValue(object value) { }
    }

    [AttributeUsage(AttributeTargets.Class | AttributeTargets.Struct | AttributeTargets.Enum | AttributeTargets.Constructor | AttributeTargets.Method | AttributeTargets.Property | AttributeTargets.Field | AttributeTargets.Event | AttributeTargets.Interface | AttributeTargets.Delegate)]
    public sealed partial class EditorBrowsableAttribute : Attribute
    {
        public EditorBrowsableAttribute() { }

        public EditorBrowsableAttribute(EditorBrowsableState state) { }

        public EditorBrowsableState State { get { throw null; } }

        public override bool Equals(object obj) { throw null; }

        public override int GetHashCode() { throw null; }
    }

    public enum EditorBrowsableState
    {
        Always = 0,
        Never = 1,
        Advanced = 2
    }
}