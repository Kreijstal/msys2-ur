extern alias sourceacl;
using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Text.Json;
using A=sourceacl::System.Security.AccessControl;
public static class Fixture
{
    static void Check(bool ok,string text){if(!ok)throw new Exception(text);}
    public static void Run(string manifest)
    {
        var asm=typeof(A.CommonAcl).Assembly;
        Check(asm.GetName().Version==new Version(6,0,0,0),"actual source assembly 6 loaded");
        Check(Convert.ToHexString(asm.GetName().GetPublicKeyToken()).ToLowerInvariant()=="b03f5f7f11d50a3a","signing identity");
        Check(asm.GetCustomAttribute<AssemblyFileVersionAttribute>().Version=="6.0.29.0","source file version");
        Check(asm.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion=="6.0.1+runtime-189fbbd88d97dd6d65515ba2da05b62eab4e5039","source revision");
        Check(Path.GetDirectoryName(asm.Location)==AppContext.GetData("source-acl-directory") as string,"source DLL location");
        var exported=asm.GetExportedTypes();Check(exported.Length>30,"full type load");
        using(var doc=JsonDocument.Parse(File.ReadAllText(manifest)))
        {
            var entry=doc.RootElement[0];
            using var rr=new ResourceReader(asm.GetManifestResourceStream(entry.GetProperty("resource").GetString()+".resources"));
            var actual=rr.Cast<DictionaryEntry>().ToDictionary(x=>(string)x.Key,x=>(string)x.Value);
            foreach(var pair in entry.GetProperty("strings").EnumerateObject())Check(actual[pair.Name]==pair.Value.GetString(),"resource "+pair.Name);
            Check(actual.Count==entry.GetProperty("strings").EnumerateObject().Count(),"resource count");
            Console.WriteLine("PASS ACL6 source identity/location, "+exported.Length+" exported types and "+actual.Count+" resources");
        }
        var sid=WindowsIdentity.GetCurrent().User;
        var world=new SecurityIdentifier(WellKnownSidType.WorldSid,null);
        var acl=new A.DiscretionaryAcl(false,false,4);
        acl.AddAccess(A.AccessControlType.Allow,sid,0x120089,A.InheritanceFlags.None,A.PropagationFlags.None);
        acl.AddAccess(A.AccessControlType.Allow,world,1,A.InheritanceFlags.None,A.PropagationFlags.None);
        Check(acl.IsCanonical && acl.Count==2,"canonical DACL");
        var sd=new A.CommonSecurityDescriptor(false,false,A.ControlFlags.DiscretionaryAclPresent,sid,sid,null,acl);
        string sddl=sd.GetSddlForm(A.AccessControlSections.All);
        var round=new A.CommonSecurityDescriptor(false,false,sddl);
        byte[] b=new byte[round.BinaryLength];round.GetBinaryForm(b,0);
        var raw=new A.RawSecurityDescriptor(b,0);Check(raw.Owner.Equals(sid)&&raw.DiscretionaryAcl.Count==2,"SDDL/binary round trip");
        var ace=new A.CommonAce(A.AceFlags.None,A.AceQualifier.AccessAllowed,123,world,false,null);
        byte[] ab=new byte[ace.BinaryLength];ace.GetBinaryForm(ab,0);var clone=A.GenericAce.CreateFromBinaryForm(ab,0);
        Check(ace==clone&&((A.CommonAce)clone).AccessMask==123,"ACE binary/equality");
        acl.RemoveAccessSpecific(A.AccessControlType.Allow,world,1,A.InheritanceFlags.None,A.PropagationFlags.None);
        Check(acl.Count==1,"DACL remove");
        var audit=new A.SystemAcl(false,false,2);
        audit.AddAudit(A.AuditFlags.Success,sid,1,A.InheritanceFlags.None,A.PropagationFlags.None);
        Check(audit.Count==1,"SACL audit construction");
        try{new A.RawSecurityDescriptor(new byte[2],0);throw new Exception("bad binary accepted");}catch(ArgumentException){}
        try{new A.RawSecurityDescriptor("invalid-sddl");throw new Exception("bad SDDL accepted");}catch(ArgumentException){}
        Console.WriteLine("PASS ACL6 native SDDL conversion, ACE/ACL binary round trips, canonicalization, audit rules and malformed inputs");
        string path=Path.Combine(Path.GetTempPath(),"msys2-acl6-"+Guid.NewGuid()+"-é.txt");
        try
        {
            File.WriteAllText(path,"owned ACL fixture");
            var security=new OwnedSecurity(path);
            var owner=security.GetOwner(typeof(SecurityIdentifier));Check(owner.Equals(sid),"native file owner");
            string prior=security.GetSecurityDescriptorSddlForm(A.AccessControlSections.Access);
            security.SetSecurityDescriptorSddlForm(prior,A.AccessControlSections.Access);
            security.Save(path);
            var reopened=new OwnedSecurity(path);
            var beforeSd=new A.RawSecurityDescriptor(prior);
            var afterSd=new A.RawSecurityDescriptor(reopened.GetSecurityDescriptorSddlForm(A.AccessControlSections.Access));
            byte[] beforeAcl=new byte[beforeSd.DiscretionaryAcl.BinaryLength],afterAcl=new byte[afterSd.DiscretionaryAcl.BinaryLength];
            beforeSd.DiscretionaryAcl.GetBinaryForm(beforeAcl,0);afterSd.DiscretionaryAcl.GetBinaryForm(afterAcl,0);
            // SetSecurityInfo can mark an inherited DACL AutoInherited. Its ACEs
            // and inheritance protection must survive persistence exactly.
            Check(beforeAcl.SequenceEqual(afterAcl),"native persist/reopen ACL bytes");
            Check((beforeSd.ControlFlags&A.ControlFlags.DiscretionaryAclProtected)==(afterSd.ControlFlags&A.ControlFlags.DiscretionaryAclProtected),"native DACL protection");
            using var file=File.Open(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete);
            var byHandle=new OwnedSecurity(file.SafeFileHandle);
            Check(byHandle.GetOwner(typeof(SecurityIdentifier)).Equals(sid),"native handle owner");
            Check(byHandle.GetAccessRules(true,true,typeof(SecurityIdentifier)).Count>0,"native access rule factories");
            Console.WriteLine("PASS ACL6 native GetSecurityInfo by Unicode filename/handle, owned-file DACL persistence and reopen");
        }
        finally{File.Delete(path);}
    }
    sealed class Rule:A.AccessRule
    {public Rule(IdentityReference id,int mask,bool inherited,A.InheritanceFlags i,A.PropagationFlags p,A.AccessControlType t):base(id,mask,inherited,i,p,t){}}
    sealed class Audit:A.AuditRule
    {public Audit(IdentityReference id,int mask,bool inherited,A.InheritanceFlags i,A.PropagationFlags p,A.AuditFlags t):base(id,mask,inherited,i,p,t){}}
    sealed class OwnedSecurity:A.NativeObjectSecurity
    {
        public OwnedSecurity(string name):base(false,A.ResourceType.FileObject,name,A.AccessControlSections.Access|A.AccessControlSections.Owner){}
        public OwnedSecurity(SafeHandle handle):base(false,A.ResourceType.FileObject,handle,A.AccessControlSections.Access|A.AccessControlSections.Owner){}
        public void Save(string name)=>Persist(name,A.AccessControlSections.Access);
        public override Type AccessRightType=>typeof(int);
        public override Type AccessRuleType=>typeof(Rule);
        public override Type AuditRuleType=>typeof(Audit);
        public override A.AccessRule AccessRuleFactory(IdentityReference id,int mask,bool inherited,A.InheritanceFlags i,A.PropagationFlags p,A.AccessControlType t)=>new Rule(id,mask,inherited,i,p,t);
        public override A.AuditRule AuditRuleFactory(IdentityReference id,int mask,bool inherited,A.InheritanceFlags i,A.PropagationFlags p,A.AuditFlags t)=>new Audit(id,mask,inherited,i,p,t);
    }
}
