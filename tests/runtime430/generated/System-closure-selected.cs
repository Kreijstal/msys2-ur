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

    public enum UriPartial
    {
        Scheme = 0,
        Authority = 1,
        Path = 2,
        Query = 3
    }

    public partial class UriTypeConverter : ComponentModel.TypeConverter
    {
        public UriTypeConverter() { }

        internal UriTypeConverter(UriKind uriKind) { }

        public override bool CanConvertFrom(ComponentModel.ITypeDescriptorContext context, Type sourceType) { throw null; }

        public override bool CanConvertTo(ComponentModel.ITypeDescriptorContext context, Type destinationType) { throw null; }

        public override object ConvertFrom(ComponentModel.ITypeDescriptorContext context, Globalization.CultureInfo culture, object value) { throw null; }

        public override object ConvertTo(ComponentModel.ITypeDescriptorContext context, Globalization.CultureInfo culture, object value, Type destinationType) { throw null; }

        public override bool IsValid(ComponentModel.ITypeDescriptorContext context, object value) { throw null; }
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
    [Runtime.InteropServices.ComVisible(true)]
    public partial class AttributeCollection : Collections.ICollection, Collections.IEnumerable
    {
        public static readonly AttributeCollection Empty;
        protected AttributeCollection() { }

        public AttributeCollection(params Attribute[] attributes) { }

        protected virtual Attribute[] Attributes { get { throw null; } }

        public int Count { get { throw null; } }

        public virtual Attribute this[int index] { get { throw null; } }

        public virtual Attribute this[Type attributeType] { get { throw null; } }

        int Collections.ICollection.Count { get { throw null; } }

        bool Collections.ICollection.IsSynchronized { get { throw null; } }

        object Collections.ICollection.SyncRoot { get { throw null; } }

        public bool Contains(Attribute attribute) { throw null; }

        public bool Contains(Attribute[] attributes) { throw null; }

        public void CopyTo(Array array, int index) { }

        public static AttributeCollection FromExisting(AttributeCollection existing, params Attribute[] newAttributes) { throw null; }

        protected Attribute GetDefaultAttribute(Type attributeType) { throw null; }

        public Collections.IEnumerator GetEnumerator() { throw null; }

        public bool Matches(Attribute attribute) { throw null; }

        public bool Matches(Attribute[] attributes) { throw null; }

        Collections.IEnumerator Collections.IEnumerable.GetEnumerator() { throw null; }
    }

    [Runtime.InteropServices.ComVisible(true)]
    public partial class ComponentCollection : Collections.ReadOnlyCollectionBase
    {
        public ComponentCollection(IComponent[] components) { }

        public virtual IComponent this[int index] { get { throw null; } }

        public virtual IComponent this[string name] { get { throw null; } }

        public void CopyTo(IComponent[] array, int index) { }
    }

    public partial class ComponentConverter : ReferenceConverter
    {
        public ComponentConverter(Type type) : base(default!) { }

        public override PropertyDescriptorCollection GetProperties(ITypeDescriptorContext context, object value, Attribute[] attributes) { throw null; }

        public override bool GetPropertiesSupported(ITypeDescriptorContext context) { throw null; }
    }

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

    [AttributeUsage(AttributeTargets.Class | AttributeTargets.Interface, AllowMultiple = true, Inherited = true)]
    public sealed partial class DesignerAttribute : Attribute
    {
        public DesignerAttribute(string designerTypeName, string designerBaseTypeName) { }

        public DesignerAttribute(string designerTypeName, Type designerBaseType) { }

        public DesignerAttribute(string designerTypeName) { }

        public DesignerAttribute(Type designerType, Type designerBaseType) { }

        public DesignerAttribute(Type designerType) { }

        public string DesignerBaseTypeName { get { throw null; } }

        public string DesignerTypeName { get { throw null; } }

        public override object TypeId { get { throw null; } }

        public override bool Equals(object obj) { throw null; }

        public override int GetHashCode() { throw null; }
    }

    [Runtime.InteropServices.ComVisible(true)]
    public enum DesignerSerializationVisibility
    {
        Hidden = 0,
        Visible = 1,
        Content = 2
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

    [Design.Serialization.RootDesignerSerializer("System.ComponentModel.Design.Serialization.RootCodeDomSerializer, System.Design, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a", "System.ComponentModel.Design.Serialization.CodeDomSerializer, System.Design, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a", true)]
    [Designer("System.ComponentModel.Design.ComponentDesigner, System.Design, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a", typeof(Design.IDesigner))]
    [Designer("System.Windows.Forms.Design.ComponentDocumentDesigner, System.Design, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a", typeof(Design.IRootDesigner))]
    [TypeConverter(typeof(ComponentConverter))]
    [Runtime.InteropServices.ComVisible(true)]
    public partial interface IComponent : IDisposable
    {
        ISite Site { get; set; }

        event EventHandler Disposed;
    }

    [Runtime.InteropServices.ComVisible(true)]
    public partial interface IContainer : IDisposable
    {
        ComponentCollection Components { get; }

        void Add(IComponent component, string name);
        void Add(IComponent component);
        void Remove(IComponent component);
    }

    [Runtime.InteropServices.ComVisible(true)]
    public partial interface ISite : IServiceProvider
    {
        IComponent Component { get; }

        IContainer Container { get; }

        bool DesignMode { get; }

        string Name { get; set; }
    }

    [Runtime.InteropServices.ComVisible(true)]
    public partial interface ITypeDescriptorContext : IServiceProvider
    {
        IContainer Container { get; }

        object Instance { get; }

        PropertyDescriptor PropertyDescriptor { get; }

        void OnComponentChanged();
        bool OnComponentChanging();
    }

    [Runtime.InteropServices.ComVisible(true)]
    public abstract partial class MemberDescriptor
    {
        protected MemberDescriptor(MemberDescriptor oldMemberDescriptor, Attribute[] newAttributes) { }

        protected MemberDescriptor(MemberDescriptor descr) { }

        protected MemberDescriptor(string name, Attribute[] attributes) { }

        protected MemberDescriptor(string name) { }

        protected virtual Attribute[] AttributeArray { get { throw null; } set { } }

        public virtual AttributeCollection Attributes { get { throw null; } }

        public virtual string Category { get { throw null; } }

        public virtual string Description { get { throw null; } }

        public virtual bool DesignTimeOnly { get { throw null; } }

        public virtual string DisplayName { get { throw null; } }

        public virtual bool IsBrowsable { get { throw null; } }

        public virtual string Name { get { throw null; } }

        protected virtual int NameHashCode { get { throw null; } }

        protected virtual AttributeCollection CreateAttributeCollection() { throw null; }

        public override bool Equals(object obj) { throw null; }

        protected virtual void FillAttributes(Collections.IList attributeList) { }

        protected static Reflection.MethodInfo FindMethod(Type componentClass, string name, Type[] args, Type returnType, bool publicOnly) { throw null; }

        protected static Reflection.MethodInfo FindMethod(Type componentClass, string name, Type[] args, Type returnType) { throw null; }

        public override int GetHashCode() { throw null; }

        protected virtual object GetInvocationTarget(Type type, object instance) { throw null; }

        [Obsolete("This method has been deprecated. Use GetInvocationTarget instead.  http://go.microsoft.com/fwlink/?linkid=14202")]
        protected static object GetInvokee(Type componentClass, object component) { throw null; }

        protected static ISite GetSite(object component) { throw null; }
    }

    [Runtime.InteropServices.ComVisible(true)]
    public abstract partial class PropertyDescriptor : MemberDescriptor
    {
        protected PropertyDescriptor(MemberDescriptor descr, Attribute[] attrs) : base(default(string)!) { }

        protected PropertyDescriptor(MemberDescriptor descr) : base(default(string)!) { }

        protected PropertyDescriptor(string name, Attribute[] attrs) : base(default(string)!) { }

        public abstract Type ComponentType { get; }

        public virtual TypeConverter Converter { get { throw null; } }

        public virtual bool IsLocalizable { get { throw null; } }

        public abstract bool IsReadOnly { get; }
        public abstract Type PropertyType { get; }

        public DesignerSerializationVisibility SerializationVisibility { get { throw null; } }

        public virtual bool SupportsChangeEvents { get { throw null; } }

        public virtual void AddValueChanged(object component, EventHandler handler) { }

        public abstract bool CanResetValue(object component);
        protected object CreateInstance(Type type) { throw null; }

        public override bool Equals(object obj) { throw null; }

        protected override void FillAttributes(Collections.IList attributeList) { }

        public PropertyDescriptorCollection GetChildProperties() { throw null; }

        public PropertyDescriptorCollection GetChildProperties(Attribute[] filter) { throw null; }

        public virtual PropertyDescriptorCollection GetChildProperties(object instance, Attribute[] filter) { throw null; }

        public PropertyDescriptorCollection GetChildProperties(object instance) { throw null; }

        public virtual object GetEditor(Type editorBaseType) { throw null; }

        public override int GetHashCode() { throw null; }

        protected override object GetInvocationTarget(Type type, object instance) { throw null; }

        protected Type GetTypeFromName(string typeName) { throw null; }

        public abstract object GetValue(object component);
        protected internal EventHandler GetValueChangedHandler(object component) { throw null; }

        protected virtual void OnValueChanged(object component, EventArgs e) { }

        public virtual void RemoveValueChanged(object component, EventHandler handler) { }

        public abstract void ResetValue(object component);
        public abstract void SetValue(object component, object value);
        public abstract bool ShouldSerializeValue(object component);
    }

    public partial class PropertyDescriptorCollection : Collections.ICollection, Collections.IEnumerable, Collections.IList, Collections.IDictionary
    {
        public static readonly PropertyDescriptorCollection Empty;
        public PropertyDescriptorCollection(PropertyDescriptor[] properties, bool readOnly) { }

        public PropertyDescriptorCollection(PropertyDescriptor[] properties) { }

        public int Count { get { throw null; } }

        public virtual PropertyDescriptor this[int index] { get { throw null; } }

        public virtual PropertyDescriptor this[string name] { get { throw null; } }

        int Collections.ICollection.Count { get { throw null; } }

        bool Collections.ICollection.IsSynchronized { get { throw null; } }

        object Collections.ICollection.SyncRoot { get { throw null; } }

        bool Collections.IDictionary.IsFixedSize { get { throw null; } }

        bool Collections.IDictionary.IsReadOnly { get { throw null; } }

        object Collections.IDictionary.this[object key] { get { throw null; } set { } }

        Collections.ICollection Collections.IDictionary.Keys { get { throw null; } }

        Collections.ICollection Collections.IDictionary.Values { get { throw null; } }

        bool Collections.IList.IsFixedSize { get { throw null; } }

        bool Collections.IList.IsReadOnly { get { throw null; } }

        object Collections.IList.this[int index] { get { throw null; } set { } }

        public int Add(PropertyDescriptor value) { throw null; }

        public void Clear() { }

        public bool Contains(PropertyDescriptor value) { throw null; }

        public void CopyTo(Array array, int index) { }

        public virtual PropertyDescriptor Find(string name, bool ignoreCase) { throw null; }

        public virtual Collections.IEnumerator GetEnumerator() { throw null; }

        public int IndexOf(PropertyDescriptor value) { throw null; }

        public void Insert(int index, PropertyDescriptor value) { }

        protected void InternalSort(Collections.IComparer sorter) { }

        protected void InternalSort(string[] names) { }

        public void Remove(PropertyDescriptor value) { }

        public void RemoveAt(int index) { }

        public virtual PropertyDescriptorCollection Sort() { throw null; }

        public virtual PropertyDescriptorCollection Sort(Collections.IComparer comparer) { throw null; }

        public virtual PropertyDescriptorCollection Sort(string[] names, Collections.IComparer comparer) { throw null; }

        public virtual PropertyDescriptorCollection Sort(string[] names) { throw null; }

        void Collections.IDictionary.Add(object key, object value) { }

        void Collections.IDictionary.Clear() { }

        bool Collections.IDictionary.Contains(object key) { throw null; }

        object Collections.IDictionary.get_Item(object key) { throw null; }

        Collections.IDictionaryEnumerator Collections.IDictionary.GetEnumerator() { throw null; }

        void Collections.IDictionary.Remove(object key) { }

        void Collections.IDictionary.set_Item(object key, object value) { }

        Collections.IEnumerator Collections.IEnumerable.GetEnumerator() { throw null; }

        int Collections.IList.Add(object value) { throw null; }

        void Collections.IList.Clear() { }

        bool Collections.IList.Contains(object value) { throw null; }

        object Collections.IList.get_Item(int index) { throw null; }

        int Collections.IList.IndexOf(object value) { throw null; }

        void Collections.IList.Insert(int index, object value) { }

        void Collections.IList.Remove(object value) { }

        void Collections.IList.RemoveAt(int index) { }

        void Collections.IList.set_Item(int index, object value) { }
    }

    public partial class ReferenceConverter : TypeConverter
    {
        public ReferenceConverter(Type type) { }

        public override bool CanConvertFrom(ITypeDescriptorContext context, Type sourceType) { throw null; }

        public override object ConvertFrom(ITypeDescriptorContext context, Globalization.CultureInfo culture, object value) { throw null; }

        public override object ConvertTo(ITypeDescriptorContext context, Globalization.CultureInfo culture, object value, Type destinationType) { throw null; }

        public override StandardValuesCollection GetStandardValues(ITypeDescriptorContext context) { throw null; }

        public override bool GetStandardValuesExclusive(ITypeDescriptorContext context) { throw null; }

        public override bool GetStandardValuesSupported(ITypeDescriptorContext context) { throw null; }

        protected virtual bool IsValueAllowed(ITypeDescriptorContext context, object value) { throw null; }
    }

    [Runtime.InteropServices.ComVisible(true)]
    public partial class TypeConverter
    {
        public virtual bool CanConvertFrom(ITypeDescriptorContext context, Type sourceType) { throw null; }

        public bool CanConvertFrom(Type sourceType) { throw null; }

        public virtual bool CanConvertTo(ITypeDescriptorContext context, Type destinationType) { throw null; }

        public bool CanConvertTo(Type destinationType) { throw null; }

        public virtual object ConvertFrom(ITypeDescriptorContext context, Globalization.CultureInfo culture, object value) { throw null; }

        public object ConvertFrom(object value) { throw null; }

        public object ConvertFromInvariantString(ITypeDescriptorContext context, string text) { throw null; }

        public object ConvertFromInvariantString(string text) { throw null; }

        public object ConvertFromString(ITypeDescriptorContext context, Globalization.CultureInfo culture, string text) { throw null; }

        public object ConvertFromString(ITypeDescriptorContext context, string text) { throw null; }

        public object ConvertFromString(string text) { throw null; }

        public virtual object ConvertTo(ITypeDescriptorContext context, Globalization.CultureInfo culture, object value, Type destinationType) { throw null; }

        public object ConvertTo(object value, Type destinationType) { throw null; }

        public string ConvertToInvariantString(ITypeDescriptorContext context, object value) { throw null; }

        public string ConvertToInvariantString(object value) { throw null; }

        public string ConvertToString(ITypeDescriptorContext context, Globalization.CultureInfo culture, object value) { throw null; }

        public string ConvertToString(ITypeDescriptorContext context, object value) { throw null; }

        public string ConvertToString(object value) { throw null; }

        public object CreateInstance(Collections.IDictionary propertyValues) { throw null; }

        public virtual object CreateInstance(ITypeDescriptorContext context, Collections.IDictionary propertyValues) { throw null; }

        protected Exception GetConvertFromException(object value) { throw null; }

        protected Exception GetConvertToException(object value, Type destinationType) { throw null; }

        public bool GetCreateInstanceSupported() { throw null; }

        public virtual bool GetCreateInstanceSupported(ITypeDescriptorContext context) { throw null; }

        public virtual PropertyDescriptorCollection GetProperties(ITypeDescriptorContext context, object value, Attribute[] attributes) { throw null; }

        public PropertyDescriptorCollection GetProperties(ITypeDescriptorContext context, object value) { throw null; }

        public PropertyDescriptorCollection GetProperties(object value) { throw null; }

        public bool GetPropertiesSupported() { throw null; }

        public virtual bool GetPropertiesSupported(ITypeDescriptorContext context) { throw null; }

        public Collections.ICollection GetStandardValues() { throw null; }

        public virtual StandardValuesCollection GetStandardValues(ITypeDescriptorContext context) { throw null; }

        public bool GetStandardValuesExclusive() { throw null; }

        public virtual bool GetStandardValuesExclusive(ITypeDescriptorContext context) { throw null; }

        public bool GetStandardValuesSupported() { throw null; }

        public virtual bool GetStandardValuesSupported(ITypeDescriptorContext context) { throw null; }

        public virtual bool IsValid(ITypeDescriptorContext context, object value) { throw null; }

        public bool IsValid(object value) { throw null; }

        protected PropertyDescriptorCollection SortProperties(PropertyDescriptorCollection props, string[] names) { throw null; }

        protected abstract partial class SimplePropertyDescriptor : PropertyDescriptor
        {
            protected SimplePropertyDescriptor(Type componentType, string name, Type propertyType, Attribute[] attributes) : base(default!) { }

            protected SimplePropertyDescriptor(Type componentType, string name, Type propertyType) : base(default!) { }

            public override Type ComponentType { get { throw null; } }

            public override bool IsReadOnly { get { throw null; } }

            public override Type PropertyType { get { throw null; } }

            public override bool CanResetValue(object component) { throw null; }

            public override void ResetValue(object component) { }

            public override bool ShouldSerializeValue(object component) { throw null; }
        }

        public partial class StandardValuesCollection : Collections.ICollection, Collections.IEnumerable
        {
            public StandardValuesCollection(Collections.ICollection values) { }

            public int Count { get { throw null; } }

            public object this[int index] { get { throw null; } }

            int Collections.ICollection.Count { get { throw null; } }

            bool Collections.ICollection.IsSynchronized { get { throw null; } }

            object Collections.ICollection.SyncRoot { get { throw null; } }

            public void CopyTo(Array array, int index) { }

            public Collections.IEnumerator GetEnumerator() { throw null; }

            void Collections.ICollection.CopyTo(Array array, int index) { }

            Collections.IEnumerator Collections.IEnumerable.GetEnumerator() { throw null; }
        }
    }

    [AttributeUsage(AttributeTargets.All)]
    public sealed partial class TypeConverterAttribute : Attribute
    {
        public static readonly TypeConverterAttribute Default;
        public TypeConverterAttribute() { }

        public TypeConverterAttribute(string typeName) { }

        public TypeConverterAttribute(Type type) { }

        public string ConverterTypeName { get { throw null; } }

        public override bool Equals(object obj) { throw null; }

        public override int GetHashCode() { throw null; }
    }
}

namespace System.ComponentModel.Design
{
    [Runtime.InteropServices.ComVisible(true)]
    public partial class CommandID
    {
        public CommandID(Guid menuGroup, int commandID) { }

        public virtual Guid Guid { get { throw null; } }

        public virtual int ID { get { throw null; } }

        public override bool Equals(object obj) { throw null; }

        public override int GetHashCode() { throw null; }

        public override string ToString() { throw null; }
    }

    [Runtime.InteropServices.ComVisible(true)]
    public partial class DesignerVerb : MenuCommand
    {
        public DesignerVerb(string text, EventHandler handler, CommandID startCommandID) : base(default!, default!) { }

        public DesignerVerb(string text, EventHandler handler) : base(default!, default!) { }

        public string Description { get { throw null; } set { } }

        public string Text { get { throw null; } }

        public override string ToString() { throw null; }
    }

    [Runtime.InteropServices.ComVisible(true)]
    public partial class DesignerVerbCollection : Collections.CollectionBase
    {
        public DesignerVerbCollection() { }

        public DesignerVerbCollection(DesignerVerb[] value) { }

        public DesignerVerb this[int index] { get { throw null; } set { } }

        public int Add(DesignerVerb value) { throw null; }

        public void AddRange(DesignerVerb[] value) { }

        public void AddRange(DesignerVerbCollection value) { }

        public bool Contains(DesignerVerb value) { throw null; }

        public void CopyTo(DesignerVerb[] array, int index) { }

        public int IndexOf(DesignerVerb value) { throw null; }

        public void Insert(int index, DesignerVerb value) { }

        protected override void OnClear() { }

        protected override void OnInsert(int index, object value) { }

        protected override void OnRemove(int index, object value) { }

        protected override void OnSet(int index, object oldValue, object newValue) { }

        protected override void OnValidate(object value) { }

        public void Remove(DesignerVerb value) { }
    }

    [Runtime.InteropServices.ComVisible(true)]
    public partial interface IDesigner : IDisposable
    {
        IComponent Component { get; }

        DesignerVerbCollection Verbs { get; }

        void DoDefaultAction();
        void Initialize(IComponent component);
    }

    [Runtime.InteropServices.ComVisible(true)]
    public partial interface IRootDesigner : IDesigner, IDisposable
    {
        ViewTechnology[] SupportedTechnologies { get; }

        object GetView(ViewTechnology technology);
    }

    [Runtime.InteropServices.ComVisible(true)]
    public partial class MenuCommand
    {
        public MenuCommand(EventHandler handler, CommandID command) { }

        public virtual bool Checked { get { throw null; } set { } }

        public virtual CommandID CommandID { get { throw null; } }

        public virtual bool Enabled { get { throw null; } set { } }

        public virtual int OleStatus { get { throw null; } }

        public virtual Collections.IDictionary Properties { get { throw null; } }

        public virtual bool Supported { get { throw null; } set { } }

        public virtual bool Visible { get { throw null; } set { } }

        public event EventHandler CommandChanged { add { } remove { } }

        public virtual void Invoke() { }

        public virtual void Invoke(object arg) { }

        protected virtual void OnCommandChanged(EventArgs e) { }

        public override string ToString() { throw null; }
    }

    [Runtime.InteropServices.ComVisible(true)]
    public enum ViewTechnology
    {
        Passthrough = 0,
        WindowsForms = 1,
        Default = 2
    }
}

namespace System.ComponentModel.Design.Serialization
{
    [AttributeUsage(AttributeTargets.Class | AttributeTargets.Interface, AllowMultiple = true, Inherited = true)]
    [Obsolete("This attribute has been deprecated. Use DesignerSerializerAttribute instead.  For example, to specify a root designer for CodeDom, use DesignerSerializerAttribute(...,typeof(TypeCodeDomSerializer)).  http://go.microsoft.com/fwlink/?linkid=14202")]
    public sealed partial class RootDesignerSerializerAttribute : Attribute
    {
        public RootDesignerSerializerAttribute(string serializerTypeName, string baseSerializerTypeName, bool reloadable) { }

        public RootDesignerSerializerAttribute(string serializerTypeName, Type baseSerializerType, bool reloadable) { }

        public RootDesignerSerializerAttribute(Type serializerType, Type baseSerializerType, bool reloadable) { }

        public bool Reloadable { get { throw null; } }

        public string SerializerBaseTypeName { get { throw null; } }

        public string SerializerTypeName { get { throw null; } }

        public override object TypeId { get { throw null; } }
    }
}