using System;
using System.Diagnostics;
using System.Linq;
using System.Management;
using System.Threading;

internal static class PersistenceChecks
{
    private static int checks;
    private static void Require(bool value, string message)
    {
        Interlocked.Increment(ref checks);
        if (!value) throw new Exception(message);
    }

    private static bool Missing(ManagementScope scope, string path)
    {
        var parsed = new ManagementPath(path);
        try
        {
            using ManagementObject item = parsed.IsClass
                ? new ManagementClass(scope, parsed, null)
                : new ManagementObject(scope, parsed, null);
            item.Get();
            return false;
        }
        catch (ManagementException error) when (error.ErrorCode == ManagementStatus.NotFound || error.ErrorCode == ManagementStatus.InvalidClass) { return true; }
    }

    private static void RunApartment(ApartmentState apartment)
    {
        string name = "MSYS2_WmiPersist_" + Guid.NewGuid().ToString("N");
        var root = new ManagementScope("root");
        root.Connect();
        string namespacePath = "__Namespace.Name=\"" + name + "\"";
        Require(Missing(root, namespacePath), "Unique namespace must be absent before creation");
        bool created = false;
        try
        {
            using (var namespaceType = new ManagementClass(root, new ManagementPath("__Namespace"), null))
            using (var instance = namespaceType.CreateInstance())
            {
                instance["Name"] = name;
                instance.Put(new PutOptions { Type = PutType.CreateOnly });
                created = true;
            }
            var scope = new ManagementScope("root\\" + name);
            scope.Connect();
            Require(!Missing(root, namespacePath), "Namespace persisted");
            const string typeName = "MSYS2_PersistedRecord";
            using (var type = new ManagementClass(scope, new ManagementPath(), null))
            {
                type["__CLASS"] = typeName;
                type.Properties.Add("Id", CimType.String, false);
                type.Properties["Id"].Qualifiers.Add("Key", true);
                type.Properties.Add("Text", CimType.String, false);
                type.Properties.Add("Counter", CimType.UInt32, false);
                var path = type.Put(new PutOptions { Type = PutType.CreateOnly });
                Require(path.ClassName == typeName, "Class Put returns persisted path");
            }
            using (var type = new ManagementClass(scope, new ManagementPath(typeName), null))
            {
                type.Get();
                Require(type.Properties["Counter"].Type == CimType.UInt32, "Reopened schema has UInt32 property");
                Require((bool)type.Properties["Id"].Qualifiers["Key"].Value, "Key qualifier persisted");
                using var instance = type.CreateInstance();
                instance["Id"] = "owned";
                instance["Text"] = "初期 café 🐚";
                instance["Counter"] = (uint)1;
                var path = instance.Put(new PutOptions { Type = PutType.CreateOnly });
                Require(path.IsInstance && path.ClassName == typeName, "Instance Put returns keyed path");
                using var reopened = new ManagementObject(scope, path, null);
                reopened.Get();
                Require((string)reopened["Text"] == "初期 café 🐚" && (uint)reopened["Counter"] == 1, "Reopened instance retains Unicode and UInt32");
                reopened["Text"] = "updated Ω";
                reopened["Counter"] = (uint)4294967295;
                reopened.Put(new PutOptions { Type = PutType.UpdateOnly });
                using var search = new ManagementObjectSearcher(scope, new ObjectQuery("SELECT * FROM " + typeName));
                using var rows = search.Get();
                Require(rows.Count == 1, "Persistent query returns one owned row");
                foreach (ManagementObject row in rows)
                {
                    using (row) Require((string)row["Text"] == "updated Ω" && (uint)row["Counter"] == uint.MaxValue, "Query observes persisted update");
                }
                using var completed = new ManualResetEventSlim();
                var observer = new ManagementOperationObserver();
                ManagementStatus status = ManagementStatus.Failed;
                string asyncPath = null;
                observer.ObjectPut += (_, args) => asyncPath = args.Path.RelativePath;
                observer.Completed += (_, args) => { status = args.Status; completed.Set(); };
                reopened["Text"] = "async retained";
                reopened.Put(observer, new PutOptions { Type = PutType.UpdateOnly });
                Require(completed.Wait(TimeSpan.FromSeconds(30)), "Async Put completes");
                Require(status == ManagementStatus.NoError && !string.IsNullOrEmpty(asyncPath), "Async Put reports path and success");
                GC.Collect(2, GCCollectionMode.Forced, true, true);
                // The original WmiEventSink uses ClassName for ObjectPut. The
                // Windows Framework control also returns a class path here.
                var reportedPath = new ManagementPath(asyncPath);
                Require(reportedPath.IsClass && reportedPath.ClassName == typeName, "Async ObjectPut class-path behavior matches independent Windows control");
                using var afterAsync = new ManagementObject(scope, path, null);
                afterAsync.Get();
                Require((string)afterAsync["Text"] == "async retained", "Async write persists after callback and GC");
                afterAsync.Delete();
                Require(Missing(scope, path.RelativePath), "Instance deletion persisted");
                type.Delete();
                Require(Missing(scope, typeName), "Class deletion persisted");
            }
        }
        finally
        {
            if (created)
            {
                using var ownedNamespace = new ManagementObject(root, new ManagementPath(namespacePath), null);
                ownedNamespace.Delete();
                Require(Missing(root, namespacePath), "Owned namespace removed");
            }
        }
        Console.WriteLine("PASS " + apartment + " persistent class/instance create/update/query/async Put/delete and namespace cleanup: " + name);
    }

    private static int Main()
    {
        try
        {
            foreach (var apartment in new[] { ApartmentState.STA, ApartmentState.MTA })
            {
                Exception failure = null;
                var thread = new Thread(() => { try { RunApartment(apartment); } catch (Exception error) { failure = error; } });
                thread.SetApartmentState(apartment);
                thread.Start();
                Require(thread.Join(TimeSpan.FromSeconds(90)), "Apartment fixture completes");
                if (failure != null) throw new Exception(apartment.ToString(), failure);
            }
            using var process = Process.GetCurrentProcess();
            var modules = process.Modules.Cast<ProcessModule>().ToArray();
            Require(modules.Any(module => module.ModuleName.Equals("msys-wmi-native.dll", StringComparison.OrdinalIgnoreCase)), "Source native backend loaded");
            Require(!modules.Any(module => module.FileName.Contains("\\Microsoft.NET\\Framework", StringComparison.OrdinalIgnoreCase) || module.ModuleName.Equals("wminet_utils.dll", StringComparison.OrdinalIgnoreCase)), "No Framework helper loaded");
            Console.WriteLine("PASS " + checks + " source WMI persistent-write/call-result/STA/MTA checks");
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
