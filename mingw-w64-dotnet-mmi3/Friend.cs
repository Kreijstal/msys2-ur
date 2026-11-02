using System;
using Microsoft.Management.Infrastructure;
// Compiled separately with each real friend assembly name/key to validate the
// internal calls used by PowerShell. This is not a PowerShell implementation.
public static class FRIEND_CLASS
{
    public static void Validate(CimInstance instance)
    {
        Guid id=Guid.NewGuid();
        instance.SetCimSessionComputerName("friend-access-check");instance.SetCimSessionInstanceId(id);
        if(instance.GetCimSessionComputerName()!="friend-access-check"||instance.GetCimSessionInstanceId()!=id)throw new Exception("PowerShell friend contract");
    }
}
