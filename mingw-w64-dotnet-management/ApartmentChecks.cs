using System;
using System.Management;
using System.Security.Principal;
using System.Threading;

internal static class ApartmentChecks
{
    static void Require(bool value,string message) { if(!value)throw new Exception(message); }

    static void InApartment(ApartmentState apartment,Action action)
    {
        Exception failure=null;
        var thread=new Thread(()=> { try { action(); } catch(Exception error) { failure=error; } });
        thread.IsBackground=true;
        thread.SetApartmentState(apartment);
        thread.Start();
        Require(thread.Join(TimeSpan.FromSeconds(60)),"WMI apartment operation timed out: "+apartment);
        if(failure!=null)throw new Exception("WMI apartment failure: "+apartment,failure);
    }

    static void Query(ManagementScope scope)
    {
        using var before=WindowsIdentity.GetCurrent(true);
        using(var search=new ManagementObjectSearcher(scope,new ObjectQuery(
            "SELECT * FROM Win32_Process WHERE ProcessId="+Environment.ProcessId)))
        using(var results=search.Get())
        using(var rows=results.GetEnumerator())
        {
            Require(rows.MoveNext(),"Apartment process row missing");
            using var row=(ManagementObject)rows.Current;
            Require(Convert.ToUInt32(row["ProcessId"])==Environment.ProcessId,"Apartment PID mismatch");
            using var owner=row.InvokeMethod("GetOwner",null,null);
            Require(Convert.ToUInt32(owner["ReturnValue"])==0&&!string.IsNullOrEmpty(owner["User"]?.ToString()),"Apartment GetOwner failed");
            Require(!rows.MoveNext(),"Unexpected extra process row");
        }
        using(var type=new ManagementClass(scope,new ManagementPath("Win32_Process"),null))
        {
            type.Get();
            Require(type.Properties["ProcessId"].Type==CimType.UInt32,"Apartment class metadata");
            Require(type.Methods["GetOwner"]!=null,"Apartment method metadata");
        }
        using var after=WindowsIdentity.GetCurrent(true);
        Require((before==null)==(after==null),"Apartment temporary token was not restored");
        if(before!=null)Require(before.User==after.User&&before.ImpersonationLevel==after.ImpersonationLevel,"Apartment thread identity changed");
    }

    internal static void Run()
    {
        foreach(bool privileges in new[]{false,true})
        {
            ManagementScope fromMta=null,fromSta=null;
            InApartment(ApartmentState.MTA,()=> { fromMta=new ManagementScope("root\\cimv2",new ConnectionOptions{EnablePrivileges=privileges});fromMta.Connect();Query(fromMta); });
            InApartment(ApartmentState.STA,()=> { Query(fromMta);fromSta=new ManagementScope("root\\cimv2",new ConnectionOptions{EnablePrivileges=privileges});fromSta.Connect();Query(fromSta); });
            InApartment(ApartmentState.MTA,()=>Query(fromSta));
        }
        Console.WriteLine("PASS STA/MTA local queries/GetOwner/class metadata, scopes shared in both directions and temporary thread-token restoration");
    }
}
