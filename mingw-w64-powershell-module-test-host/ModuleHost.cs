// Test-only host for the original source-built PowerShell engine and cmdlets.
// The shipping pwsh ConsoleHost and full SDK dependency graph remain separate.
using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Management.Automation;
using System.Management.Automation.Runspaces;
using System.Reflection;

static class ModuleHost
{
    static int Main(string[] args)
    {
        try
        {
            if (args.Length == 0) throw new ArgumentException("usage: powershell-module-test-host SCRIPT [SCRIPT_ARGUMENT ...]");
            string cultureName = Environment.GetEnvironmentVariable("SOURCE_POWERSHELL_TEST_CULTURE");
            if (!string.IsNullOrEmpty(cultureName))
            {
                var culture = System.Globalization.CultureInfo.GetCultureInfo(cultureName);
                System.Globalization.CultureInfo.CurrentCulture = culture;
                System.Globalization.CultureInfo.CurrentUICulture = culture;
            }
            var engine = typeof(PowerShell).Assembly;
            if (engine.GetName().Version != new Version(7,4,6,500) ||
                !engine.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion.Contains("013edf910bbe781f503c27370941ce54d02d3f33"))
                throw new Exception("unexpected source PowerShell engine identity");
            var initial = InitialSessionState.CreateDefault2();
            initial.ExecutionPolicy = Microsoft.PowerShell.ExecutionPolicy.Bypass;
            initial.Variables.Add(new SessionStateVariableEntry("PSModuleAutoLoadingPreference", "None", "Only explicitly supplied source modules"));
            initial.Variables.Add(new SessionStateVariableEntry("ProgressPreference", ActionPreference.SilentlyContinue, "Owned test host"));
            foreach (string name in new[] { "Microsoft.PowerShell.Security", "Microsoft.PowerShell.Management", "Microsoft.PowerShell.Utility", "CimCmdlets" })
                initial.ImportPSModule(new[] { Path.Combine(AppContext.BaseDirectory, name+".psd1") });
            using var runspace = RunspaceFactory.CreateRunspace(initial); runspace.Open();
            using var shell = PowerShell.Create(); shell.Runspace = runspace;
            shell.AddCommand(Path.GetFullPath(args[0]));
            foreach (string argument in args.Skip(1)) shell.AddArgument(argument);
            foreach (var value in shell.Invoke()) Console.WriteLine(value?.ToString());
            foreach (var warning in shell.Streams.Warning) Console.Error.WriteLine("WARNING " + warning.Message);
            foreach (var error in shell.Streams.Error) Console.Error.WriteLine("ERROR " + error.FullyQualifiedErrorId + ": " + error.Exception);
            if (shell.InvocationStateInfo.State != PSInvocationState.Completed || shell.Streams.Error.Count != 0)
                throw new Exception("script failed: " + shell.InvocationStateInfo.State + "; " + shell.InvocationStateInfo.Reason);
            foreach (ProcessModule module in Process.GetCurrentProcess().Modules)
                if (module.FileName.Replace('\\','/').Contains("/Microsoft.NET/Framework", StringComparison.OrdinalIgnoreCase))
                    throw new Exception("Framework implementation loaded: " + module.FileName);
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
