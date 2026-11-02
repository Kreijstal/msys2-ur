using System;
using Microsoft.Build.Utilities;
using Microsoft.DotNet.Build.Tasks;

// The historical release used a UTC build host. Its task converts locally parsed
// midnight to UTC, which moves the calendar day on the current Windows builder.
// Exercise the unchanged version algorithm with the original UTC calendar date.
public sealed class CheckReleaseVersion : Task
{
    public override bool Execute()
    {
        var original = new GenerateCurrentVersion { Padding = 5 };
        string version = original.GetCurrentVersionForDate(new DateTime(2017, 7, 19, 0, 0, 0, DateTimeKind.Utc), null);
        bool parsed = original.SetVersionAndRevisionFromBuildId("20170719.03");
        if (!parsed || version != "25519" || original.GeneratedRevision != "03")
        {
            Log.LogError("Original UTC release version algorithm mismatch");
            return false;
        }
        Log.LogMessage("PASS unchanged original UTC date algorithm=25519; original build revision=03");
        return true;
    }
}
