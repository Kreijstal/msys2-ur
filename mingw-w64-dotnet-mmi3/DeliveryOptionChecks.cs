using System;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Security;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Internal;
using Microsoft.Management.Infrastructure.Native;
using Microsoft.Management.Infrastructure.Options;

static class DeliveryOptionChecks
{
    static int checks;
    static void Require(bool value,string message){checks++;if(!value)throw new Exception(message);}
    static void Ok(MI_Result result){Require(result==MI_Result.MI_RESULT_OK,"Native delivery result: "+result);}
    static void Throws<T>(Action action,string parameter=null) where T:Exception
    {
        try{action();}catch(T error){Require(parameter==null || error is ArgumentException argument && argument.ParamName==parameter,"Exception parameter: "+parameter);(error as IDisposable)?.Dispose();return;}
        throw new Exception("Expected "+typeof(T).Name);
    }
    static uint Count(CimSubscriptionDeliveryOptions options)
    {
        Ok(options.SubscriptionDeliveryOptionsHandle.GetCredentialsCount(out uint count));return count;
    }
    static TimeSpan Interval(CimSubscriptionDeliveryOptions options,string name)
    {
        using var native=new MI_Value();
        Ok(options.SubscriptionDeliveryOptionsHandle.GetOption(name,native,out MI_Type type,out _,out _));
        Require(type==MI_Type.MI_DATETIME,"Interval native type");
        return (TimeSpan)native.Datetime.ConvertFromNativeLayer();
    }
    static void Baseline()
    {
        Throws<InvalidCastException>(()=>new CimSubscriptionDeliveryOptions());
        // Construct valid native state independently to reach the remaining
        // public methods despite the installed managed constructor's ABI bug.
        var app=CimApplication.Handle;
        var ft=(MI_Application.MI_ApplicationFT)typeof(MI_Application).GetProperty("ft",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(app);
        var native=MI_SubscriptionDeliveryOptions.NewDirectPtr();
        Ok(ft.NewSubscriptionDeliveryOptions(app,MI_SubscriptionDeliveryType.MI_SubscriptionDeliveryType_Push,native));
        var wrapper=(CimSubscriptionDeliveryOptions)RuntimeHelpers.GetUninitializedObject(typeof(CimSubscriptionDeliveryOptions));
        typeof(CimSubscriptionDeliveryOptions).GetField("_subscriptionDeliveryOptionsHandle",BindingFlags.Instance|BindingFlags.NonPublic).SetValue(wrapper,native);
        try
        {
            wrapper.AddCredentials("fixture",new CimCredential(ImpersonatedAuthenticationMechanism.Negotiate),0);
            Require(Count(wrapper)==0,"Expected no-op credential addition");
            wrapper.SetInterval("interval",TimeSpan.FromSeconds(17),0);
            Require(Interval(wrapper,"interval")==TimeSpan.Zero,"Expected dropped interval value");
            Throws<InvalidCastException>(()=>new CimSubscriptionDeliveryOptions(wrapper));
        }
        finally{wrapper.Dispose();native.Dispose();}
        Console.WriteLine("REPRODUCED delivery-options constructor/clone ABI failures, no-op AddCredentials and zeroed interval");
    }
    static void Inspect(CimSubscriptionDeliveryOptions options,string name,string auth,string domain=null,string user=null,string password=null,string thumbprint=null)
    {
        var handle=options.SubscriptionDeliveryOptionsHandle;
        // Native MI enumerates option names without insertion-order guarantees.
        object[] args=null;uint index=0;
        for(uint i=0;i<Count(options);i++)
        {
            object[] entry={i,null,new MI_UserCredentials(),null};
            Ok((MI_Result)typeof(MI_SubscriptionDeliveryOptions).GetMethod("GetCredentialsAt",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(handle,entry));
            if((string)entry[1]==name){args=entry;index=i;break;}
        }
        Require(args!=null,"Credential option found by name: "+name);
        var value=(MI_UserCredentials)args[2];
        Require((string)args[1]==name && (uint)args[3]==0,"Credential option name/flags");
        Require(value.authenticationTypeString==auth,"Credential mechanism");
        if(thumbprint!=null)Require(MI_PlatformSpecific.PtrToString(value.credentials.certificateThumbprint)==thumbprint,"Certificate union/ownership");
        else
        {
            Require((MI_PlatformSpecific.PtrToString(value.credentials.usernamePassword.domain)??"")==(domain??""),"Credential domain");
            Require((MI_PlatformSpecific.PtrToString(value.credentials.usernamePassword.username)??"")==(user??""),"Credential user");
            if(password!=null)
            {
                object[] sizing={index,null,IntPtr.Zero,(uint)0,null,null};
                typeof(MI_SubscriptionDeliveryOptions).GetMethod("GetCredentialsPasswordAt",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(handle,sizing);
                uint length=(uint)sizing[4];Require(length>0,"Native password buffer size");
                IntPtr buffer=Marshal.AllocHGlobal(checked((int)length*2));
                try
                {
                    object[] reading={index,null,buffer,length,null,null};
                    Ok((MI_Result)typeof(MI_SubscriptionDeliveryOptions).GetMethod("GetCredentialsPasswordAt",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(handle,reading));
                    Require(Marshal.PtrToStringUni(buffer)==password,"Password copied into native options");
                }
                finally{for(int i=0;i<checked((int)length*2);i++)Marshal.WriteByte(buffer,i,0);Marshal.FreeHGlobal(buffer);}
            }
        }
    }
    static void Exercise()
    {
        foreach(var mode in new[]{CimSubscriptionDeliveryType.None,CimSubscriptionDeliveryType.Push,CimSubscriptionDeliveryType.Pull})
        {
            using var options=new CimSubscriptionDeliveryOptions(mode);
            Require(Count(options)==0,"Empty delivery credential store");
            options.SetString("label","雪 λ",0);options.SetNumber("number",42,0);
            Ok(options.SubscriptionDeliveryOptionsHandle.GetString("label",out string text,out _,out _));Require(text=="雪 λ","Native string option");
            Ok(options.SubscriptionDeliveryOptionsHandle.GetNumber("number",out uint number,out _,out _));Require(number==42,"Native numeric option");
            var timestamp=new DateTime(2026,11,8,12,13,14,DateTimeKind.Utc).AddTicks(1234560);
            options.SetDateTime("timestamp",timestamp,0);
            using(var value=new MI_Value())
            {
                Ok(options.SubscriptionDeliveryOptionsHandle.GetOption("timestamp",value,out MI_Type type,out _,out _));
                Require(type==MI_Type.MI_DATETIME && ((DateTime)value.Datetime.ConvertFromNativeLayer()).ToUniversalTime()==timestamp,"Native timestamp option");
            }
            options.SetDateTime("duration",TimeSpan.FromTicks(171234560),0);
            Require(Interval(options,"duration")==TimeSpan.FromTicks(171234560),"Native duration datetime overload");
            foreach(var interval in new[]{TimeSpan.Zero,TimeSpan.FromTicks(123456789),new TimeSpan(3,4,5,6,789),TimeSpan.MaxValue})
            {
                options.SetInterval("interval",interval,0);
                var expected=interval==TimeSpan.MaxValue?interval:TimeSpan.FromTicks(interval.Ticks/10*10);
                Require(Interval(options,"interval")==expected,"Native interval precision/sentinel");
            }
            Throws<ArgumentOutOfRangeException>(()=>options.SetInterval("interval",TimeSpan.FromTicks(-1),0));
        }
        using var original=new CimSubscriptionDeliveryOptions();
        const string secret="fixture-π-密碼";
        using var password=new SecureString();foreach(char c in secret)password.AppendChar(c);
        var credential=new CimCredential(PasswordAuthenticationMechanism.Negotiate,"fixture-domain-é","fixture-user-名",password);
        password.Clear();password.Dispose();
        original.AddCredentials("password",credential,0);
        Inspect(original,"password","NegoWithCreds","fixture-domain-é","fixture-user-名",secret);
        original.AddCredentials("implicit",new CimCredential(ImpersonatedAuthenticationMechanism.Negotiate),0);
        Inspect(original,"implicit","NegoNoCreds");
        original.AddCredentials("certificate",new CimCredential(CertificateAuthenticationMechanism.ClientCertificate,"0123456789ABCDEF0123456789ABCDEF01234567"),0);
        Inspect(original,"certificate","ClientCerts",thumbprint:"0123456789ABCDEF0123456789ABCDEF01234567");
        Require(Count(original)==3,"All native credential entries stored");
        original.SetInterval("retained",TimeSpan.FromSeconds(17.123456),0);
        using var clone=new CimSubscriptionDeliveryOptions(original);
        original.Dispose();original.Dispose();
        GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();
        Require(Count(clone)==3,"Cloned credentials survive original disposal/GC");
        Inspect(clone,"password","NegoWithCreds","fixture-domain-é","fixture-user-名",secret);
        Inspect(clone,"implicit","NegoNoCreds");Inspect(clone,"certificate","ClientCerts",thumbprint:"0123456789ABCDEF0123456789ABCDEF01234567");
        Require(Interval(clone,"retained")==TimeSpan.FromTicks(171234560),"Clone retains interval");
        var local=new CimSubscriptionDeliveryOptions();
        Throws<ArgumentNullException>(()=>local.AddCredentials(null,credential,0),"optionName");
        Throws<ArgumentNullException>(()=>local.AddCredentials("valid",null,0),"optionValue");
        Throws<ArgumentNullException>(()=>new CimSubscriptionDeliveryOptions(null),"optionsToClone");
        var raw=local.SubscriptionDeliveryOptionsHandle;
        local.Dispose();local.Dispose();Require(raw.Ptr==IntPtr.Zero,"Dispose releases direct native wrapper allocation");
        Throws<ObjectDisposedException>(()=>local.SetString("x","x",0));
        Throws<ObjectDisposedException>(()=>local.AddCredentials("x",credential,0));
        Throws<ObjectDisposedException>(()=>new CimSubscriptionDeliveryOptions(local));
    }
    static int Main(string[] args)
    {
        try
        {
            if(args.Contains("--baseline")){Baseline();return 0;}
            Exercise();Console.WriteLine("PASS "+checks+" native delivery option/credential/interval/clone/disposal checks");return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
}
