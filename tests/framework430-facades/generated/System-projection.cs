namespace System
{
    [ComponentModel.TypeConverter(typeof(UriTypeConverter))]
    public partial class Uri : Runtime.Serialization.ISerializable
    {
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

        public bool UserEscaped { get { throw null; } }

        public string UserInfo { get { throw null; } }

        [Obsolete("The method has been deprecated. It is not used by the system. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected virtual void Canonicalize() { }

        public static UriHostNameType CheckHostName(string name) { throw null; }

        public static bool CheckSchemeName(string schemeName) { throw null; }

        [Obsolete("The method has been deprecated. It is not used by the system. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected virtual void CheckSecurity() { }

        public static int Compare(Uri uri1, Uri uri2, UriComponents partsToCompare, UriFormat compareFormat, StringComparison comparisonType) { throw null; }

        public override bool Equals(object comparand) { throw null; }

        [Obsolete("The method has been deprecated. It is not used by the system. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected virtual void Escape() { }

        public static string EscapeDataString(string stringToEscape) { throw null; }

        [Obsolete("The method has been deprecated. Please use GetComponents() or static EscapeUriString() to escape a Uri component or a string. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected static string EscapeString(string str) { throw null; }

        public static string EscapeUriString(string stringToEscape) { throw null; }

        public static int FromHex(char digit) { throw null; }

        public string GetComponents(UriComponents components, UriFormat format) { throw null; }

        public override int GetHashCode() { throw null; }

        public string GetLeftPart(UriPartial part) { throw null; }

        protected void GetObjectData(Runtime.Serialization.SerializationInfo serializationInfo, Runtime.Serialization.StreamingContext streamingContext) { }

        public static string HexEscape(char character) { throw null; }

        public static char HexUnescape(string pattern, ref int index) { throw null; }

        [Obsolete("The method has been deprecated. It is not used by the system. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected virtual bool IsBadFileSystemCharacter(char character) { throw null; }

        public bool IsBaseOf(Uri uri) { throw null; }

        [Obsolete("The method has been deprecated. It is not used by the system. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected static bool IsExcludedCharacter(char character) { throw null; }

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

        void Runtime.Serialization.ISerializable.GetObjectData(Runtime.Serialization.SerializationInfo serializationInfo, Runtime.Serialization.StreamingContext streamingContext) { }

        public override string ToString() { throw null; }

        public static bool TryCreate(string uriString, UriKind uriKind, out Uri result) { throw null; }

        public static bool TryCreate(Uri baseUri, string relativeUri, out Uri result) { throw null; }

        public static bool TryCreate(Uri baseUri, Uri relativeUri, out Uri result) { throw null; }

        [Obsolete("The method has been deprecated. Please use GetComponents() or static UnescapeDataString() to unescape a Uri component or a string. http://go.microsoft.com/fwlink/?linkid=14202")]
        protected virtual string Unescape(string path) { throw null; }

        public static string UnescapeDataString(string stringToUnescape) { throw null; }
    }

    public partial class UriBuilder
    {
        public UriBuilder() { }

        public UriBuilder(string scheme, string host, int port, string path, string extraValue) { }

        public UriBuilder(string scheme, string host, int port, string pathValue) { }

        public UriBuilder(string scheme, string host, int portNumber) { }

        public UriBuilder(string schemeName, string hostName) { }

        public UriBuilder(string uri) { }

        public UriBuilder(Uri uri) { }

        public string Fragment { get { throw null; } set { } }

        public string Host { get { throw null; } set { } }

        public string Password { get { throw null; } set { } }

        public string Path { get { throw null; } set { } }

        public int Port { get { throw null; } set { } }

        public string Query { get { throw null; } set { } }

        public string Scheme { get { throw null; } set { } }

        public Uri Uri { get { throw null; } }

        public string UserName { get { throw null; } set { } }

        public override bool Equals(object rparam) { throw null; }

        public override int GetHashCode() { throw null; }

        public override string ToString() { throw null; }
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
        public override bool CanConvertFrom(ComponentModel.ITypeDescriptorContext context, Type sourceType) { throw null; }

        public override bool CanConvertTo(ComponentModel.ITypeDescriptorContext context, Type destinationType) { throw null; }

        public override object ConvertFrom(ComponentModel.ITypeDescriptorContext context, Globalization.CultureInfo culture, object value) { throw null; }

        public override object ConvertTo(ComponentModel.ITypeDescriptorContext context, Globalization.CultureInfo culture, object value, Type destinationType) { throw null; }

        public override bool IsValid(ComponentModel.ITypeDescriptorContext context, object value) { throw null; }
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


        Collections.IDictionaryEnumerator Collections.IDictionary.GetEnumerator() { throw null; }

        void Collections.IDictionary.Remove(object key) { }


        Collections.IEnumerator Collections.IEnumerable.GetEnumerator() { throw null; }

        int Collections.IList.Add(object value) { throw null; }

        void Collections.IList.Clear() { }

        bool Collections.IList.Contains(object value) { throw null; }


        int Collections.IList.IndexOf(object value) { throw null; }

        void Collections.IList.Insert(int index, object value) { }

        void Collections.IList.Remove(object value) { }

        void Collections.IList.RemoveAt(int index) { }

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

    [Security.SuppressUnmanagedCodeSecurity]
    public partial class Win32Exception : Runtime.InteropServices.ExternalException, Runtime.Serialization.ISerializable
    {
        public Win32Exception() { }

        public Win32Exception(int error, string message) { }

        public Win32Exception(int error) { }

        protected Win32Exception(Runtime.Serialization.SerializationInfo info, Runtime.Serialization.StreamingContext context) { }

        public Win32Exception(string message, Exception innerException) { }

        public Win32Exception(string message) { }

        public int NativeErrorCode { get { throw null; } }

        public override void GetObjectData(Runtime.Serialization.SerializationInfo info, Runtime.Serialization.StreamingContext context) { }
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

namespace System.Diagnostics
{
    public partial class Stopwatch
    {
        public static readonly long Frequency;
        public static readonly bool IsHighResolution;
        public TimeSpan Elapsed { get { throw null; } }

        public long ElapsedMilliseconds { get { throw null; } }

        public long ElapsedTicks { get { throw null; } }

        public bool IsRunning { get { throw null; } }

        public static long GetTimestamp() { throw null; }

        public void Reset() { }

        public void Restart() { }

        public void Start() { }

        public static Stopwatch StartNew() { throw null; }

        public void Stop() { }
    }
}

namespace System.Net
{
    public abstract partial class EndPoint
    {
        public virtual Sockets.AddressFamily AddressFamily { get { throw null; } }

        public virtual EndPoint Create(SocketAddress socketAddress) { throw null; }

        public virtual SocketAddress Serialize() { throw null; }
    }

    public partial class IPAddress
    {
        public static readonly IPAddress Any;
        public static readonly IPAddress Broadcast;
        public static readonly IPAddress IPv6Any;
        public static readonly IPAddress IPv6Loopback;
        public static readonly IPAddress IPv6None;
        public static readonly IPAddress Loopback;
        public static readonly IPAddress None;
        public IPAddress(byte[] address, long scopeid) { }

        public IPAddress(byte[] address) { }

        public IPAddress(long newAddress) { }

        [Obsolete("This property has been deprecated. It is address family dependent. Please use IPAddress.Equals method to perform comparisons. http://go.microsoft.com/fwlink/?linkid=14202")]
        public long Address { get { throw null; } set { } }

        public Sockets.AddressFamily AddressFamily { get { throw null; } }

        public bool IsIPv4MappedToIPv6 { get { throw null; } }

        public bool IsIPv6LinkLocal { get { throw null; } }

        public bool IsIPv6Multicast { get { throw null; } }

        public bool IsIPv6SiteLocal { get { throw null; } }

        public bool IsIPv6Teredo { get { throw null; } }

        public long ScopeId { get { throw null; } set { } }

        public override bool Equals(object comparand) { throw null; }

        public byte[] GetAddressBytes() { throw null; }

        public override int GetHashCode() { throw null; }

        public static short HostToNetworkOrder(short host) { throw null; }

        public static int HostToNetworkOrder(int host) { throw null; }

        public static long HostToNetworkOrder(long host) { throw null; }

        public static bool IsLoopback(IPAddress address) { throw null; }

        public IPAddress MapToIPv4() { throw null; }

        public IPAddress MapToIPv6() { throw null; }

        public static short NetworkToHostOrder(short network) { throw null; }

        public static int NetworkToHostOrder(int network) { throw null; }

        public static long NetworkToHostOrder(long network) { throw null; }

        public static IPAddress Parse(string ipString) { throw null; }

        public override string ToString() { throw null; }

        public static bool TryParse(string ipString, out IPAddress address) { throw null; }
    }

    public partial class IPEndPoint : EndPoint
    {
        public const int MaxPort = 65535;
        public const int MinPort = 0;
        public IPEndPoint(long address, int port) { }

        public IPEndPoint(IPAddress address, int port) { }

        public IPAddress Address { get { throw null; } set { } }

        public override Sockets.AddressFamily AddressFamily { get { throw null; } }

        public int Port { get { throw null; } set { } }

        public override EndPoint Create(SocketAddress socketAddress) { throw null; }

        public override bool Equals(object comparand) { throw null; }

        public override int GetHashCode() { throw null; }

        public override SocketAddress Serialize() { throw null; }

        public override string ToString() { throw null; }
    }

    public partial class SocketAddress
    {
        public SocketAddress(Sockets.AddressFamily family, int size) { }

        public SocketAddress(Sockets.AddressFamily family) { }

        public Sockets.AddressFamily Family { get { throw null; } }

        public byte this[int offset] { get { throw null; } set { } }

        public int Size { get { throw null; } }

        public override bool Equals(object comparand) { throw null; }

        public override int GetHashCode() { throw null; }

        public override string ToString() { throw null; }
    }

    public static partial class WebUtility
    {
        public static void HtmlDecode(string value, IO.TextWriter output) { }

        public static string HtmlDecode(string value) { throw null; }

        public static void HtmlEncode(string value, IO.TextWriter output) { }

        public static string HtmlEncode(string value) { throw null; }

        public static string UrlDecode(string encodedValue) { throw null; }

        public static byte[] UrlDecodeToBytes(byte[] encodedValue, int offset, int count) { throw null; }

        public static string UrlEncode(string value) { throw null; }

        public static byte[] UrlEncodeToBytes(byte[] value, int offset, int count) { throw null; }
    }
}

namespace System.Net.Sockets
{
    public enum AddressFamily
    {
        Unknown = -1,
        Unspecified = 0,
        Unix = 1,
        InterNetwork = 2,
        ImpLink = 3,
        Pup = 4,
        Chaos = 5,
        Ipx = 6,
        NS = 6,
        Iso = 7,
        Osi = 7,
        Ecma = 8,
        DataKit = 9,
        Ccitt = 10,
        Sna = 11,
        DecNet = 12,
        DataLink = 13,
        Lat = 14,
        HyperChannel = 15,
        AppleTalk = 16,
        NetBios = 17,
        VoiceView = 18,
        FireFox = 19,
        Banyan = 21,
        Atm = 22,
        InterNetworkV6 = 23,
        Cluster = 24,
        Ieee12844 = 25,
        Irda = 26,
        NetworkDesigners = 28,
        Max = 29
    }

    public enum IOControlCode : long
    {
        AsyncIO = 2147772029L,
        NonBlockingIO = 2147772030L,
        AssociateHandle = 2281701377L,
        MultipointLoopback = 2281701385L,
        MulticastScope = 2281701386L,
        SetQos = 2281701387L,
        SetGroupQos = 2281701388L,
        RoutingInterfaceChange = 2281701397L,
        NamespaceChange = 2281701401L,
        ReceiveAll = 2550136833L,
        ReceiveAllMulticast = 2550136834L,
        ReceiveAllIgmpMulticast = 2550136835L,
        KeepAliveValues = 2550136836L,
        AbsorbRouterAlert = 2550136837L,
        UnicastInterface = 2550136838L,
        LimitBroadcasts = 2550136839L,
        BindToInterface = 2550136840L,
        MulticastInterface = 2550136841L,
        AddMulticastGroupOnInterface = 2550136842L,
        DeleteMulticastGroupFromInterface = 2550136843L,
        GetExtensionFunctionPointer = 3355443206L,
        GetQos = 3355443207L,
        GetGroupQos = 3355443208L,
        TranslateHandle = 3355443213L,
        RoutingInterfaceQuery = 3355443220L,
        AddressListSort = 3355443225L,
        EnableCircularQueuing = 671088642L,
        Flush = 671088644L,
        AddressListChange = 671088663L,
        DataToRead = 1074030207L,
        OobDataRead = 1074033415L,
        GetBroadcastAddress = 1207959557L,
        AddressListQuery = 1207959574L,
        QueryTargetPnpHandle = 1207959576L
    }

    public partial struct IPPacketInformation
    {
        private object _dummy;
        private int _dummyPrimitive;
        public IPAddress Address { get { throw null; } }

        public int Interface { get { throw null; } }

        public override bool Equals(object comparand) { throw null; }

        public override int GetHashCode() { throw null; }

        public static bool operator ==(IPPacketInformation packetInformation1, IPPacketInformation packetInformation2) { throw null; }

        public static bool operator !=(IPPacketInformation packetInformation1, IPPacketInformation packetInformation2) { throw null; }
    }

    public enum IPProtectionLevel
    {
        Unspecified = -1,
        Unrestricted = 10,
        EdgeRestricted = 20,
        Restricted = 30
    }

    public partial class IPv6MulticastOption
    {
        public IPv6MulticastOption(IPAddress group, long ifindex) { }

        public IPv6MulticastOption(IPAddress group) { }

        public IPAddress Group { get { throw null; } set { } }

        public long InterfaceIndex { get { throw null; } set { } }
    }

    public partial class LingerOption
    {
        public LingerOption(bool enable, int seconds) { }

        public bool Enabled { get { throw null; } set { } }

        public int LingerTime { get { throw null; } set { } }
    }

    public partial class MulticastOption
    {
        public MulticastOption(IPAddress group, int interfaceIndex) { }

        public MulticastOption(IPAddress group, IPAddress mcint) { }

        public MulticastOption(IPAddress group) { }

        public IPAddress Group { get { throw null; } set { } }

        public int InterfaceIndex { get { throw null; } set { } }

        public IPAddress LocalAddress { get { throw null; } set { } }
    }

    public partial class NetworkStream : IO.Stream
    {
        public NetworkStream(Socket socket, bool ownsSocket) { }

        public NetworkStream(Socket socket, IO.FileAccess access, bool ownsSocket) { }

        public NetworkStream(Socket socket, IO.FileAccess access) { }

        public NetworkStream(Socket socket) { }

        public override bool CanRead { get { throw null; } }

        public override bool CanSeek { get { throw null; } }

        public override bool CanTimeout { get { throw null; } }

        public override bool CanWrite { get { throw null; } }

        public virtual bool DataAvailable { get { throw null; } }

        public override long Length { get { throw null; } }

        public override long Position { get { throw null; } set { } }

        protected bool Readable { get { throw null; } set { } }

        public override int ReadTimeout { get { throw null; } set { } }

        protected Socket Socket { get { throw null; } }

        protected bool Writeable { get { throw null; } set { } }

        public override int WriteTimeout { get { throw null; } set { } }

        public override IAsyncResult BeginRead(byte[] buffer, int offset, int size, AsyncCallback callback, object state) { throw null; }

        public override IAsyncResult BeginWrite(byte[] buffer, int offset, int size, AsyncCallback callback, object state) { throw null; }

        public void Close(int timeout) { }

        protected override void Dispose(bool disposing) { }

        public override int EndRead(IAsyncResult asyncResult) { throw null; }

        public override void EndWrite(IAsyncResult asyncResult) { }

        ~NetworkStream() {
        }

        public override void Flush() { }

        public override Threading.Tasks.Task FlushAsync(Threading.CancellationToken cancellationToken) { throw null; }

        public override int Read(byte[] buffer, int offset, int size) { throw null; }

        public override long Seek(long offset, IO.SeekOrigin origin) { throw null; }

        public override void SetLength(long value) { }

        public override void Write(byte[] buffer, int offset, int size) { }
    }

    public enum ProtocolType
    {
        Unknown = -1,
        IP = 0,
        IPv6HopByHopOptions = 0,
        Unspecified = 0,
        Icmp = 1,
        Igmp = 2,
        Ggp = 3,
        IPv4 = 4,
        Tcp = 6,
        Pup = 12,
        Udp = 17,
        Idp = 22,
        IPv6 = 41,
        IPv6RoutingHeader = 43,
        IPv6FragmentHeader = 44,
        IPSecEncapsulatingSecurityPayload = 50,
        IPSecAuthenticationHeader = 51,
        IcmpV6 = 58,
        IPv6NoNextHeader = 59,
        IPv6DestinationOptions = 60,
        ND = 77,
        Raw = 255,
        Ipx = 1000,
        Spx = 1256,
        SpxII = 1257
    }

    public enum SelectMode
    {
        SelectRead = 0,
        SelectWrite = 1,
        SelectError = 2
    }

    public partial class SendPacketsElement
    {
        public SendPacketsElement(byte[] buffer, int offset, int count, bool endOfPacket) { }

        public SendPacketsElement(byte[] buffer, int offset, int count) { }

        public SendPacketsElement(byte[] buffer) { }

        public SendPacketsElement(string filepath, int offset, int count, bool endOfPacket) { }

        public SendPacketsElement(string filepath, int offset, int count) { }

        public SendPacketsElement(string filepath) { }

        public byte[] Buffer { get { throw null; } }

        public int Count { get { throw null; } }

        public bool EndOfPacket { get { throw null; } }

        public string FilePath { get { throw null; } }

        public int Offset { get { throw null; } }
    }

    public partial class Socket : IDisposable
    {
        public Socket(AddressFamily addressFamily, SocketType socketType, ProtocolType protocolType) { }

        public Socket(SocketInformation socketInformation) { }

        public Socket(SocketType socketType, ProtocolType protocolType) { }

        public AddressFamily AddressFamily { get { throw null; } }

        public int Available { get { throw null; } }

        public bool Blocking { get { throw null; } set { } }

        public bool Connected { get { throw null; } }

        public bool DontFragment { get { throw null; } set { } }

        public bool DualMode { get { throw null; } set { } }

        public bool EnableBroadcast { get { throw null; } set { } }

        public bool ExclusiveAddressUse { get { throw null; } set { } }

        public IntPtr Handle { get { throw null; } }

        public bool IsBound { get { throw null; } }

        public LingerOption LingerState { get { throw null; } set { } }

        public EndPoint LocalEndPoint { get { throw null; } }

        public bool MulticastLoopback { get { throw null; } set { } }

        public bool NoDelay { get { throw null; } set { } }

        public static bool OSSupportsIPv4 { get { throw null; } }

        public static bool OSSupportsIPv6 { get { throw null; } }

        public ProtocolType ProtocolType { get { throw null; } }

        public int ReceiveBufferSize { get { throw null; } set { } }

        public int ReceiveTimeout { get { throw null; } set { } }

        public EndPoint RemoteEndPoint { get { throw null; } }

        public int SendBufferSize { get { throw null; } set { } }

        public int SendTimeout { get { throw null; } set { } }

        public SocketType SocketType { get { throw null; } }

        [Obsolete("SupportsIPv4 is obsoleted for this type, please use OSSupportsIPv4 instead. http://go.microsoft.com/fwlink/?linkid=14202")]
        public static bool SupportsIPv4 { get { throw null; } }

        [Obsolete("SupportsIPv6 is obsoleted for this type, please use OSSupportsIPv6 instead. http://go.microsoft.com/fwlink/?linkid=14202")]
        public static bool SupportsIPv6 { get { throw null; } }

        public short Ttl { get { throw null; } set { } }

        public bool UseOnlyOverlappedIO { get { throw null; } set { } }

        public Socket Accept() { throw null; }

        public bool AcceptAsync(SocketAsyncEventArgs e) { throw null; }

        public IAsyncResult BeginAccept(AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginAccept(int receiveSize, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginAccept(Socket acceptSocket, int receiveSize, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginConnect(EndPoint remoteEP, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginConnect(IPAddress address, int port, AsyncCallback requestCallback, object state) { throw null; }

        public IAsyncResult BeginConnect(IPAddress[] addresses, int port, AsyncCallback requestCallback, object state) { throw null; }

        public IAsyncResult BeginConnect(string host, int port, AsyncCallback requestCallback, object state) { throw null; }

        public IAsyncResult BeginDisconnect(bool reuseSocket, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginReceive(byte[] buffer, int offset, int size, SocketFlags socketFlags, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginReceive(byte[] buffer, int offset, int size, SocketFlags socketFlags, out SocketError errorCode, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginReceive(Collections.Generic.IList<ArraySegment<byte>> buffers, SocketFlags socketFlags, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginReceive(Collections.Generic.IList<ArraySegment<byte>> buffers, SocketFlags socketFlags, out SocketError errorCode, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginReceiveFrom(byte[] buffer, int offset, int size, SocketFlags socketFlags, ref EndPoint remoteEP, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginReceiveMessageFrom(byte[] buffer, int offset, int size, SocketFlags socketFlags, ref EndPoint remoteEP, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginSend(byte[] buffer, int offset, int size, SocketFlags socketFlags, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginSend(byte[] buffer, int offset, int size, SocketFlags socketFlags, out SocketError errorCode, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginSend(Collections.Generic.IList<ArraySegment<byte>> buffers, SocketFlags socketFlags, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginSend(Collections.Generic.IList<ArraySegment<byte>> buffers, SocketFlags socketFlags, out SocketError errorCode, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginSendFile(string fileName, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginSendFile(string fileName, byte[] preBuffer, byte[] postBuffer, TransmitFileOptions flags, AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginSendTo(byte[] buffer, int offset, int size, SocketFlags socketFlags, EndPoint remoteEP, AsyncCallback callback, object state) { throw null; }

        public void Bind(EndPoint localEP) { }

        public static void CancelConnectAsync(SocketAsyncEventArgs e) { }

        public void Close() { }

        public void Close(int timeout) { }

        public void Connect(EndPoint remoteEP) { }

        public void Connect(IPAddress address, int port) { }

        public void Connect(IPAddress[] addresses, int port) { }

        public void Connect(string host, int port) { }

        public bool ConnectAsync(SocketAsyncEventArgs e) { throw null; }

        public static bool ConnectAsync(SocketType socketType, ProtocolType protocolType, SocketAsyncEventArgs e) { throw null; }

        public void Disconnect(bool reuseSocket) { }

        public bool DisconnectAsync(SocketAsyncEventArgs e) { throw null; }

        public void Dispose() { }

        protected virtual void Dispose(bool disposing) { }

        public SocketInformation DuplicateAndClose(int targetProcessId) { throw null; }

        public Socket EndAccept(out byte[] buffer, IAsyncResult asyncResult) { throw null; }

        public Socket EndAccept(out byte[] buffer, out int bytesTransferred, IAsyncResult asyncResult) { throw null; }

        public Socket EndAccept(IAsyncResult asyncResult) { throw null; }

        public void EndConnect(IAsyncResult asyncResult) { }

        public void EndDisconnect(IAsyncResult asyncResult) { }

        public int EndReceive(IAsyncResult asyncResult, out SocketError errorCode) { throw null; }

        public int EndReceive(IAsyncResult asyncResult) { throw null; }

        public int EndReceiveFrom(IAsyncResult asyncResult, ref EndPoint endPoint) { throw null; }

        public int EndReceiveMessageFrom(IAsyncResult asyncResult, ref SocketFlags socketFlags, ref EndPoint endPoint, out IPPacketInformation ipPacketInformation) { throw null; }

        public int EndSend(IAsyncResult asyncResult, out SocketError errorCode) { throw null; }

        public int EndSend(IAsyncResult asyncResult) { throw null; }

        public void EndSendFile(IAsyncResult asyncResult) { }

        public int EndSendTo(IAsyncResult asyncResult) { throw null; }

        ~Socket() {
        }

        public void GetSocketOption(SocketOptionLevel optionLevel, SocketOptionName optionName, byte[] optionValue) { }

        public byte[] GetSocketOption(SocketOptionLevel optionLevel, SocketOptionName optionName, int optionLength) { throw null; }

        public object GetSocketOption(SocketOptionLevel optionLevel, SocketOptionName optionName) { throw null; }

        public int IOControl(int ioControlCode, byte[] optionInValue, byte[] optionOutValue) { throw null; }

        public int IOControl(IOControlCode ioControlCode, byte[] optionInValue, byte[] optionOutValue) { throw null; }

        public void Listen(int backlog) { }

        public bool Poll(int microSeconds, SelectMode mode) { throw null; }

        public int Receive(byte[] buffer, int offset, int size, SocketFlags socketFlags, out SocketError errorCode) { throw null; }

        public int Receive(byte[] buffer, int offset, int size, SocketFlags socketFlags) { throw null; }

        public int Receive(byte[] buffer, int size, SocketFlags socketFlags) { throw null; }

        public int Receive(byte[] buffer, SocketFlags socketFlags) { throw null; }

        public int Receive(byte[] buffer) { throw null; }

        public int Receive(Collections.Generic.IList<ArraySegment<byte>> buffers, SocketFlags socketFlags, out SocketError errorCode) { throw null; }

        public int Receive(Collections.Generic.IList<ArraySegment<byte>> buffers, SocketFlags socketFlags) { throw null; }

        public int Receive(Collections.Generic.IList<ArraySegment<byte>> buffers) { throw null; }

        public bool ReceiveAsync(SocketAsyncEventArgs e) { throw null; }

        public int ReceiveFrom(byte[] buffer, int offset, int size, SocketFlags socketFlags, ref EndPoint remoteEP) { throw null; }

        public int ReceiveFrom(byte[] buffer, int size, SocketFlags socketFlags, ref EndPoint remoteEP) { throw null; }

        public int ReceiveFrom(byte[] buffer, ref EndPoint remoteEP) { throw null; }

        public int ReceiveFrom(byte[] buffer, SocketFlags socketFlags, ref EndPoint remoteEP) { throw null; }

        public bool ReceiveFromAsync(SocketAsyncEventArgs e) { throw null; }

        public int ReceiveMessageFrom(byte[] buffer, int offset, int size, ref SocketFlags socketFlags, ref EndPoint remoteEP, out IPPacketInformation ipPacketInformation) { throw null; }

        public bool ReceiveMessageFromAsync(SocketAsyncEventArgs e) { throw null; }

        public static void Select(Collections.IList checkRead, Collections.IList checkWrite, Collections.IList checkError, int microSeconds) { }

        public int Send(byte[] buffer, int offset, int size, SocketFlags socketFlags, out SocketError errorCode) { throw null; }

        public int Send(byte[] buffer, int offset, int size, SocketFlags socketFlags) { throw null; }

        public int Send(byte[] buffer, int size, SocketFlags socketFlags) { throw null; }

        public int Send(byte[] buffer, SocketFlags socketFlags) { throw null; }

        public int Send(byte[] buffer) { throw null; }

        public int Send(Collections.Generic.IList<ArraySegment<byte>> buffers, SocketFlags socketFlags, out SocketError errorCode) { throw null; }

        public int Send(Collections.Generic.IList<ArraySegment<byte>> buffers, SocketFlags socketFlags) { throw null; }

        public int Send(Collections.Generic.IList<ArraySegment<byte>> buffers) { throw null; }

        public bool SendAsync(SocketAsyncEventArgs e) { throw null; }

        public void SendFile(string fileName, byte[] preBuffer, byte[] postBuffer, TransmitFileOptions flags) { }

        public void SendFile(string fileName) { }

        public bool SendPacketsAsync(SocketAsyncEventArgs e) { throw null; }

        public int SendTo(byte[] buffer, int offset, int size, SocketFlags socketFlags, EndPoint remoteEP) { throw null; }

        public int SendTo(byte[] buffer, int size, SocketFlags socketFlags, EndPoint remoteEP) { throw null; }

        public int SendTo(byte[] buffer, EndPoint remoteEP) { throw null; }

        public int SendTo(byte[] buffer, SocketFlags socketFlags, EndPoint remoteEP) { throw null; }

        public bool SendToAsync(SocketAsyncEventArgs e) { throw null; }

        public void SetIPProtectionLevel(IPProtectionLevel level) { }

        public void SetSocketOption(SocketOptionLevel optionLevel, SocketOptionName optionName, bool optionValue) { }

        public void SetSocketOption(SocketOptionLevel optionLevel, SocketOptionName optionName, byte[] optionValue) { }

        public void SetSocketOption(SocketOptionLevel optionLevel, SocketOptionName optionName, int optionValue) { }

        public void SetSocketOption(SocketOptionLevel optionLevel, SocketOptionName optionName, object optionValue) { }

        public void Shutdown(SocketShutdown how) { }
    }

    public partial class SocketAsyncEventArgs : EventArgs, IDisposable
    {
        public Socket AcceptSocket { get { throw null; } set { } }

        public byte[] Buffer { get { throw null; } }

        public Collections.Generic.IList<ArraySegment<byte>> BufferList { get { throw null; } set { } }

        public int BytesTransferred { get { throw null; } }

        public Exception ConnectByNameError { get { throw null; } }

        public Socket ConnectSocket { get { throw null; } }

        public int Count { get { throw null; } }

        public bool DisconnectReuseSocket { get { throw null; } set { } }

        public SocketAsyncOperation LastOperation { get { throw null; } }

        public int Offset { get { throw null; } }

        public IPPacketInformation ReceiveMessageFromPacketInfo { get { throw null; } }

        public EndPoint RemoteEndPoint { get { throw null; } set { } }

        public SendPacketsElement[] SendPacketsElements { get { throw null; } set { } }

        public TransmitFileOptions SendPacketsFlags { get { throw null; } set { } }

        public int SendPacketsSendSize { get { throw null; } set { } }

        [Obsolete("This API supports the .NET Framework infrastructure and is not intended to be used directly from your code.", true)]
        [ComponentModel.EditorBrowsable(ComponentModel.EditorBrowsableState.Never)]
        public SocketClientAccessPolicyProtocol SocketClientAccessPolicyProtocol { get { throw null; } set { } }

        public SocketError SocketError { get { throw null; } set { } }

        public SocketFlags SocketFlags { get { throw null; } set { } }

        public object UserToken { get { throw null; } set { } }

        public event EventHandler<SocketAsyncEventArgs> Completed { add { } remove { } }

        public void Dispose() { }

        ~SocketAsyncEventArgs() {
        }

        protected virtual void OnCompleted(SocketAsyncEventArgs e) { }

        public void SetBuffer(byte[] buffer, int offset, int count) { }

        public void SetBuffer(int offset, int count) { }
    }

    public enum SocketAsyncOperation
    {
        None = 0,
        Accept = 1,
        Connect = 2,
        Disconnect = 3,
        Receive = 4,
        ReceiveFrom = 5,
        ReceiveMessageFrom = 6,
        Send = 7,
        SendPackets = 8,
        SendTo = 9
    }

    [Obsolete("This API supports the .NET Framework infrastructure and is not intended to be used directly from your code.", true)]
    [ComponentModel.EditorBrowsable(ComponentModel.EditorBrowsableState.Never)]
    public enum SocketClientAccessPolicyProtocol
    {
        Tcp = 0,
        Http = 1
    }

    public enum SocketError
    {
        SocketError = -1,
        Success = 0,
        OperationAborted = 995,
        IOPending = 997,
        Interrupted = 10004,
        AccessDenied = 10013,
        Fault = 10014,
        InvalidArgument = 10022,
        TooManyOpenSockets = 10024,
        WouldBlock = 10035,
        InProgress = 10036,
        AlreadyInProgress = 10037,
        NotSocket = 10038,
        DestinationAddressRequired = 10039,
        MessageSize = 10040,
        ProtocolType = 10041,
        ProtocolOption = 10042,
        ProtocolNotSupported = 10043,
        SocketNotSupported = 10044,
        OperationNotSupported = 10045,
        ProtocolFamilyNotSupported = 10046,
        AddressFamilyNotSupported = 10047,
        AddressAlreadyInUse = 10048,
        AddressNotAvailable = 10049,
        NetworkDown = 10050,
        NetworkUnreachable = 10051,
        NetworkReset = 10052,
        ConnectionAborted = 10053,
        ConnectionReset = 10054,
        NoBufferSpaceAvailable = 10055,
        IsConnected = 10056,
        NotConnected = 10057,
        Shutdown = 10058,
        TimedOut = 10060,
        ConnectionRefused = 10061,
        HostDown = 10064,
        HostUnreachable = 10065,
        ProcessLimit = 10067,
        SystemNotReady = 10091,
        VersionNotSupported = 10092,
        NotInitialized = 10093,
        Disconnecting = 10101,
        TypeNotFound = 10109,
        HostNotFound = 11001,
        TryAgain = 11002,
        NoRecovery = 11003,
        NoData = 11004
    }

    [Flags]
    public enum SocketFlags
    {
        None = 0,
        OutOfBand = 1,
        Peek = 2,
        DontRoute = 4,
        MaxIOVectorLength = 16,
        Truncated = 256,
        ControlDataTruncated = 512,
        Broadcast = 1024,
        Multicast = 2048,
        Partial = 32768
    }

    public partial struct SocketInformation
    {
        private object _dummy;
        private int _dummyPrimitive;
        public SocketInformationOptions Options { get { throw null; } set { } }

        public byte[] ProtocolInformation { get { throw null; } set { } }
    }

    [Flags]
    public enum SocketInformationOptions
    {
        NonBlocking = 1,
        Connected = 2,
        Listening = 4,
        UseOnlyOverlappedIO = 8
    }

    public enum SocketOptionLevel
    {
        IP = 0,
        Tcp = 6,
        Udp = 17,
        IPv6 = 41,
        Socket = 65535
    }

    public enum SocketOptionName
    {
        DontLinger = -129,
        ExclusiveAddressUse = -5,
        Debug = 1,
        IPOptions = 1,
        NoChecksum = 1,
        NoDelay = 1,
        AcceptConnection = 2,
        BsdUrgent = 2,
        Expedited = 2,
        HeaderIncluded = 2,
        TypeOfService = 3,
        IpTimeToLive = 4,
        ReuseAddress = 4,
        KeepAlive = 8,
        MulticastInterface = 9,
        MulticastTimeToLive = 10,
        MulticastLoopback = 11,
        AddMembership = 12,
        DropMembership = 13,
        DontFragment = 14,
        AddSourceMembership = 15,
        DontRoute = 16,
        DropSourceMembership = 16,
        BlockSource = 17,
        UnblockSource = 18,
        PacketInformation = 19,
        ChecksumCoverage = 20,
        HopLimit = 21,
        IPProtectionLevel = 23,
        IPv6Only = 27,
        Broadcast = 32,
        UseLoopback = 64,
        Linger = 128,
        OutOfBandInline = 256,
        SendBuffer = 4097,
        ReceiveBuffer = 4098,
        SendLowWater = 4099,
        ReceiveLowWater = 4100,
        SendTimeout = 4101,
        ReceiveTimeout = 4102,
        Error = 4103,
        Type = 4104,
        ReuseUnicastPort = 12295,
        UpdateAcceptContext = 28683,
        UpdateConnectContext = 28688,
        MaxConnections = int.MaxValue
    }

    public enum SocketShutdown
    {
        Receive = 0,
        Send = 1,
        Both = 2
    }

    public enum SocketType
    {
        Unknown = -1,
        Stream = 1,
        Dgram = 2,
        Raw = 3,
        Rdm = 4,
        Seqpacket = 5
    }

    public partial class TcpClient : IDisposable
    {
        public TcpClient() { }

        public TcpClient(IPEndPoint localEP) { }

        public TcpClient(AddressFamily family) { }

        public TcpClient(string hostname, int port) { }

        protected bool Active { get { throw null; } set { } }

        public int Available { get { throw null; } }

        public Socket Client { get { throw null; } set { } }

        public bool Connected { get { throw null; } }

        public bool ExclusiveAddressUse { get { throw null; } set { } }

        public LingerOption LingerState { get { throw null; } set { } }

        public bool NoDelay { get { throw null; } set { } }

        public int ReceiveBufferSize { get { throw null; } set { } }

        public int ReceiveTimeout { get { throw null; } set { } }

        public int SendBufferSize { get { throw null; } set { } }

        public int SendTimeout { get { throw null; } set { } }

        public IAsyncResult BeginConnect(IPAddress address, int port, AsyncCallback requestCallback, object state) { throw null; }

        public IAsyncResult BeginConnect(IPAddress[] addresses, int port, AsyncCallback requestCallback, object state) { throw null; }

        public IAsyncResult BeginConnect(string host, int port, AsyncCallback requestCallback, object state) { throw null; }

        public void Close() { }

        public void Connect(IPAddress address, int port) { }

        public void Connect(IPAddress[] ipAddresses, int port) { }

        public void Connect(IPEndPoint remoteEP) { }

        public void Connect(string hostname, int port) { }

        public Threading.Tasks.Task ConnectAsync(IPAddress address, int port) { throw null; }

        public Threading.Tasks.Task ConnectAsync(IPAddress[] addresses, int port) { throw null; }

        public Threading.Tasks.Task ConnectAsync(string host, int port) { throw null; }

        public void Dispose() { }

        protected virtual void Dispose(bool disposing) { }

        public void EndConnect(IAsyncResult asyncResult) { }

        ~TcpClient() {
        }

        public NetworkStream GetStream() { throw null; }
    }

    public partial class TcpListener
    {
        [Obsolete("This method has been deprecated. Please use TcpListener(IPAddress localaddr, int port) instead. http://go.microsoft.com/fwlink/?linkid=14202")]
        public TcpListener(int port) { }

        public TcpListener(IPAddress localaddr, int port) { }

        public TcpListener(IPEndPoint localEP) { }

        protected bool Active { get { throw null; } }

        public bool ExclusiveAddressUse { get { throw null; } set { } }

        public EndPoint LocalEndpoint { get { throw null; } }

        public Socket Server { get { throw null; } }

        public Socket AcceptSocket() { throw null; }

        public Threading.Tasks.Task<Socket> AcceptSocketAsync() { throw null; }

        public TcpClient AcceptTcpClient() { throw null; }

        public Threading.Tasks.Task<TcpClient> AcceptTcpClientAsync() { throw null; }

        public void AllowNatTraversal(bool allowed) { }

        public IAsyncResult BeginAcceptSocket(AsyncCallback callback, object state) { throw null; }

        public IAsyncResult BeginAcceptTcpClient(AsyncCallback callback, object state) { throw null; }

        public static TcpListener Create(int port) { throw null; }

        public Socket EndAcceptSocket(IAsyncResult asyncResult) { throw null; }

        public TcpClient EndAcceptTcpClient(IAsyncResult asyncResult) { throw null; }

        public bool Pending() { throw null; }

        public void Start() { }

        public void Start(int backlog) { }

        public void Stop() { }
    }

    [Flags]
    public enum TransmitFileOptions
    {
        UseDefaultWorkerThread = 0,
        Disconnect = 1,
        ReuseSocket = 2,
        WriteBehind = 4,
        UseSystemThread = 16,
        UseKernelApc = 32
    }

    public partial class UdpClient : IDisposable
    {
        public UdpClient() { }

        public UdpClient(int port, AddressFamily family) { }

        public UdpClient(int port) { }

        public UdpClient(IPEndPoint localEP) { }

        public UdpClient(AddressFamily family) { }

        public UdpClient(string hostname, int port) { }

        protected bool Active { get { throw null; } set { } }

        public int Available { get { throw null; } }

        public Socket Client { get { throw null; } set { } }

        public bool DontFragment { get { throw null; } set { } }

        public bool EnableBroadcast { get { throw null; } set { } }

        public bool ExclusiveAddressUse { get { throw null; } set { } }

        public bool MulticastLoopback { get { throw null; } set { } }

        public short Ttl { get { throw null; } set { } }

        public void AllowNatTraversal(bool allowed) { }

        public IAsyncResult BeginReceive(AsyncCallback requestCallback, object state) { throw null; }

        public IAsyncResult BeginSend(byte[] datagram, int bytes, AsyncCallback requestCallback, object state) { throw null; }

        public IAsyncResult BeginSend(byte[] datagram, int bytes, IPEndPoint endPoint, AsyncCallback requestCallback, object state) { throw null; }

        public IAsyncResult BeginSend(byte[] datagram, int bytes, string hostname, int port, AsyncCallback requestCallback, object state) { throw null; }

        public void Close() { }

        public void Connect(IPAddress addr, int port) { }

        public void Connect(IPEndPoint endPoint) { }

        public void Connect(string hostname, int port) { }

        public void Dispose() { }

        protected virtual void Dispose(bool disposing) { }

        public void DropMulticastGroup(IPAddress multicastAddr, int ifindex) { }

        public void DropMulticastGroup(IPAddress multicastAddr) { }

        public byte[] EndReceive(IAsyncResult asyncResult, ref IPEndPoint remoteEP) { throw null; }

        public int EndSend(IAsyncResult asyncResult) { throw null; }

        public void JoinMulticastGroup(int ifindex, IPAddress multicastAddr) { }

        public void JoinMulticastGroup(IPAddress multicastAddr, int timeToLive) { }

        public void JoinMulticastGroup(IPAddress multicastAddr, IPAddress localAddress) { }

        public void JoinMulticastGroup(IPAddress multicastAddr) { }

        public byte[] Receive(ref IPEndPoint remoteEP) { throw null; }

        public Threading.Tasks.Task<UdpReceiveResult> ReceiveAsync() { throw null; }

        public int Send(byte[] dgram, int bytes, IPEndPoint endPoint) { throw null; }

        public int Send(byte[] dgram, int bytes, string hostname, int port) { throw null; }

        public int Send(byte[] dgram, int bytes) { throw null; }

        public Threading.Tasks.Task<int> SendAsync(byte[] datagram, int bytes, IPEndPoint endPoint) { throw null; }

        public Threading.Tasks.Task<int> SendAsync(byte[] datagram, int bytes, string hostname, int port) { throw null; }

        public Threading.Tasks.Task<int> SendAsync(byte[] datagram, int bytes) { throw null; }
    }

    public partial struct UdpReceiveResult : IEquatable<UdpReceiveResult>
    {
        private object _dummy;
        private int _dummyPrimitive;

        public UdpReceiveResult(byte[] buffer, IPEndPoint remoteEndPoint) { }

        public byte[] Buffer { get { throw null; } }

        public IPEndPoint RemoteEndPoint { get { throw null; } }

        public bool Equals(UdpReceiveResult other) { throw null; }

        public override bool Equals(object obj) { throw null; }

        public override int GetHashCode() { throw null; }

        public static bool operator ==(UdpReceiveResult left, UdpReceiveResult right) { throw null; }

        public static bool operator !=(UdpReceiveResult left, UdpReceiveResult right) { throw null; }
    }
}

namespace System.Runtime.Versioning
{
    public sealed partial class FrameworkName : IEquatable<FrameworkName>
    {
        public FrameworkName(string identifier, Version version, string profile) { }

        public FrameworkName(string identifier, Version version) { }

        public FrameworkName(string frameworkName) { }

        public string FullName { get { throw null; } }

        public string Identifier { get { throw null; } }

        public string Profile { get { throw null; } }

        public Version Version { get { throw null; } }

        public override bool Equals(object obj) { throw null; }

        public bool Equals(FrameworkName other) { throw null; }

        public override int GetHashCode() { throw null; }

        public static bool operator ==(FrameworkName left, FrameworkName right) { throw null; }

        public static bool operator !=(FrameworkName left, FrameworkName right) { throw null; }

        public override string ToString() { throw null; }
    }
}