using System;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Threading;
static class Program {
 static void Require(bool condition) { if (!condition) throw new Exception("ACL validation failed"); }
 static void Main() {
  var sid=WindowsIdentity.GetCurrent().User;
  string name="Local\\Msys2AclTest-"+Guid.NewGuid();
  var security=new MutexSecurity();
  security.AddAccessRule(new MutexAccessRule(sid,MutexRights.FullControl,AccessControlType.Allow));
  using var mutex=MutexAcl.Create(true,name,out bool created,security); Require(created);
  var rules=mutex.GetAccessControl().GetAccessRules(true,false,typeof(SecurityIdentifier));
  Require(rules.Count>0);
  using var reopened=MutexAcl.OpenExisting(name,MutexRights.Synchronize|MutexRights.Modify);
  bool acquired=true;
  var thread=new Thread(()=>{acquired=reopened.WaitOne(50);if(acquired)reopened.ReleaseMutex();});thread.Start();thread.Join();Require(!acquired);
  mutex.ReleaseMutex();Require(reopened.WaitOne(1000));reopened.ReleaseMutex();
  var eventSecurity=new EventWaitHandleSecurity();eventSecurity.AddAccessRule(new EventWaitHandleAccessRule(sid,EventWaitHandleRights.FullControl,AccessControlType.Allow));
  using var ev=EventWaitHandleAcl.Create(false,EventResetMode.AutoReset,name+"-event",out created,eventSecurity);Require(created);ev.Set();Require(ev.WaitOne(1000));Require(ev.GetAccessControl().GetAccessRules(true,false,typeof(SecurityIdentifier)).Count>0);
  var semaphoreSecurity=new SemaphoreSecurity();semaphoreSecurity.AddAccessRule(new SemaphoreAccessRule(sid,SemaphoreRights.FullControl,AccessControlType.Allow));
  using var semaphore=SemaphoreAcl.Create(0,1,name+"-semaphore",out created,semaphoreSecurity);Require(created);semaphore.Release();Require(semaphore.WaitOne(1000));Require(semaphore.GetAccessControl().GetAccessRules(true,false,typeof(SecurityIdentifier)).Count>0);
  Console.WriteLine("PASS: native named mutex, event and semaphore ACLs; reopen and mutex contention");
 }
}
