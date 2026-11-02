namespace System
{
    internal partial interface ITuple
    {
        int Size { get; }

        int GetHashCode(Collections.IEqualityComparer comparer);
        string ToString(Text.StringBuilder sb);
    }
}

namespace System.Runtime.Remoting
{
    internal partial class Identity
    {
        private Identity() { }
    }

    internal partial class ServerIdentity : Identity
    {
        private ServerIdentity() { }
    }
}

namespace System.Runtime.Remoting.Messaging
{
    internal partial interface IInternalMessage
    {
        Identity IdentityObject { get; set; }

        ServerIdentity ServerIdentityObject { get; set; }

        [Security.SecurityCritical]
        bool HasProperties();
        [Security.SecurityCritical]
        void SetCallContext(LogicalCallContext callContext);
        [Security.SecurityCritical]
        void SetURI(string uri);
    }

    internal partial interface ISerializationRootObject
    {
        [Security.SecurityCritical]
        void RootSetObjectData(Serialization.SerializationInfo info, Serialization.StreamingContext ctx);
    }
}

namespace System.Security
{
    internal partial interface ISecurityElementFactory
    {
        string Attribute(string attributeName);
        object Copy();
        SecurityElement CreateSecurityElement();
        string GetTag();
    }
}

namespace System.Security.Permissions
{
    internal partial interface IBuiltInPermission
    {
        int GetTokenIndex();
    }
}

namespace System.Security.Policy
{
    internal partial interface IConstantMembershipCondition
    {
    }

    internal partial interface IDelayEvaluatedEvidence
    {
        bool IsVerified { get; }

        bool WasUsed { get; }

        void MarkUsed();
    }

    internal partial interface IReportMatchMembershipCondition
    {
        bool Check(Evidence evidence, out object usedEvidence);
    }

    internal partial interface IUnionSemanticCodeGroup
    {
        PolicyStatement InternalResolve(Evidence evidence);
    }
}

namespace System.Threading
{
    internal partial interface IAsyncLocal
    {
        [Security.SecurityCritical]
        void OnValueChanged(object previousValue, object currentValue, bool contextChanged);
    }

    internal partial interface IThreadPoolWorkItem
    {
        [Security.SecurityCritical]
        void ExecuteWorkItem();
        [Security.SecurityCritical]
        void MarkAborted(ThreadAbortException tae);
    }
}