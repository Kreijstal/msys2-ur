using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Resources;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Text;

internal static class Program
{
    static void Require(bool condition, string message) { if (!condition) throw new Exception(message); }
    static int Main(string[] args)
    {
        var path = Path.GetFullPath(args[0]);
        var context = new AssemblyLoadContext("original-protecteddata44", isCollectible: true);
        var produced = context.LoadFromAssemblyPath(path);
        Require(produced.Location == path, "isolated produced assembly path");
        var runner = context.LoadFromAssemblyPath(typeof(Program).Assembly.Location);
        runner.GetType("Program")!.GetMethod("Run", BindingFlags.NonPublic | BindingFlags.Static)!
            .Invoke(null, new object[] { path, args[1] });
        return 0;
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    static void Run(string path, string expectedResourceFile)
    {
        var assembly = typeof(ProtectedData).Assembly;
        Require(assembly.Location == path, "actual produced implementation executed");
        Require(assembly.GetName().Version!.ToString() == "4.0.2.0", "original assembly version");
        Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant() == "b03f5f7f11d50a3a", "MSFT public key");
        Require(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>()!.Version == "4.6.25519.03", "original release file version");
        Require(!assembly.GetCustomAttributesData().Any(a => a.AttributeType.FullName == "System.Runtime.Versioning.TargetFrameworkAttribute"), "original absence of target framework attribute");
        Require(!assembly.GetReferencedAssemblies().Any(a => a.Name == "System.Private.CoreLib" || a.Version!.Major >= 8), "original NETStandard reference identity closure");
        Require(assembly.GetCustomAttribute<DefaultDllImportSearchPathsAttribute>()!.Paths ==
            (DllImportSearchPath.AssemblyDirectory | DllImportSearchPath.System32), "original native DLL search policy");
        Require(assembly.GetCustomAttribute<CLSCompliantAttribute>()!.IsCompliant, "original CLS compliance policy");
        var data = Encoding.UTF8.GetBytes("Grüße 世界 DPAPI \0 in-memory test");
        var entropy = Encoding.UTF8.GetBytes("独立 Entropie");
        foreach (var scope in new[] { DataProtectionScope.CurrentUser, DataProtectionScope.LocalMachine })
        {
            foreach (var input in new[] { data, Array.Empty<byte>() })
            {
                Console.WriteLine("DPAPI scope=" + scope + " input-bytes=" + input.Length);
                var native = NativeTransform(input, entropy, true, scope);
                Require(NativeTransform(native, entropy, false, scope).SequenceEqual(input), "independent native round trip, including empty input");
                Console.WriteLine("PASS independent native DPAPI input-bytes=" + input.Length);
                var before = input.ToArray();
                var encrypted = ProtectedData.Protect(input, entropy, scope);
                Require(encrypted.Length > 0 && input.SequenceEqual(before), "encryption and input lifetime");
                Require(ProtectedData.Unprotect(encrypted, entropy, scope).SequenceEqual(input), "both scopes and empty-input round trip");
                Require(NativeTransform(encrypted, entropy, false, scope).SequenceEqual(input), "produced encryption / native decryption interoperability");
                Require(ProtectedData.Unprotect(native, entropy, scope).SequenceEqual(input), "native encryption / produced decryption interoperability");
            }
        }
        var withoutEntropy = ProtectedData.Protect(data, null!, DataProtectionScope.CurrentUser);
        Require(ProtectedData.Unprotect(withoutEntropy, null!, DataProtectionScope.CurrentUser).SequenceEqual(data), "null entropy");
        var withEntropy = ProtectedData.Protect(data, entropy, DataProtectionScope.CurrentUser);
        RequireThrows<CryptographicException>(() => ProtectedData.Unprotect(withEntropy, Encoding.UTF8.GetBytes("wrong"), DataProtectionScope.CurrentUser), "wrong entropy error");
        RequireThrows<CryptographicException>(() => ProtectedData.Unprotect(new byte[] { 1, 2, 3 }, entropy, DataProtectionScope.CurrentUser), "malformed data error");
        RequireThrows<ArgumentNullException>(() => ProtectedData.Protect(null!, null!, DataProtectionScope.CurrentUser), "null protect input");
        RequireThrows<ArgumentNullException>(() => ProtectedData.Unprotect(null!, null!, DataProtectionScope.CurrentUser), "null unprotect input");
        Require(ProtectedData.Unprotect(withoutEntropy, null!, (DataProtectionScope)12345).SequenceEqual(data), "original unknown scope-bit compatibility");
        var expected = System.Text.Json.JsonSerializer.Deserialize<System.Collections.Generic.Dictionary<string, string>>(File.ReadAllText(expectedResourceFile))!;
        using (var stream = assembly.GetManifestResourceStream("FxResources.System.Security.Cryptography.ProtectedData.SR.resources")!)
        using (var reader = new ResourceReader(stream))
        {
            int count = 0;
            foreach (DictionaryEntry entry in reader)
            {
                Require(expected[(string)entry.Key] == (string)entry.Value!, "original resource value");
                count++;
            }
            Require(count == expected.Count && count == 2, "complete original neutral resource set");
        }
        using (var pe = new PEReader(File.OpenRead(path)))
        using (var pdb = MetadataReaderProvider.FromPortablePdbStream(File.OpenRead(Path.ChangeExtension(path, ".pdb"))))
        {
            var cv = pe.ReadCodeViewDebugDirectoryData(pe.ReadDebugDirectory().Single(e => e.Type == DebugDirectoryEntryType.CodeView));
            Require(cv.Guid == new Guid(pdb.GetMetadataReader().DebugMetadataHeader!.Id.Take(16).ToArray()), "portable PDB identity");
        }
        Console.WriteLine("PASS produced ProtectedData4.4 original Windows NETStandard implementation: identities, both scopes, Unicode/empty/null input, entropy/errors, native DPAPI interoperability, two resources and PDB identity");
    }

    static void RequireThrows<T>(Action action, string label) where T : Exception
    { try { action(); } catch (T) { return; } throw new Exception(label); }

    [StructLayout(LayoutKind.Sequential)]
    struct Blob { public int Length; public IntPtr Data; }
    [DllImport("crypt32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool CryptProtectData(ref Blob data, string? description, ref Blob entropy, IntPtr reserved, IntPtr prompt, int flags, out Blob output);
    [DllImport("crypt32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool CryptUnprotectData(ref Blob data, IntPtr description, ref Blob entropy, IntPtr reserved, IntPtr prompt, int flags, out Blob output);
    [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr memory);
    static byte[] NativeTransform(byte[] input, byte[] entropy, bool encrypt, DataProtectionScope scope)
    {
        var a = GCHandle.Alloc(input, GCHandleType.Pinned);
        var b = GCHandle.Alloc(entropy, GCHandleType.Pinned);
        Blob result = default;
        try
        {
            var data = new Blob { Length = input.Length, Data = a.AddrOfPinnedObject() };
            var salt = new Blob { Length = entropy.Length, Data = b.AddrOfPinnedObject() };
            int flags = 1 | (scope == DataProtectionScope.LocalMachine ? 4 : 0);
            bool ok = encrypt ? CryptProtectData(ref data, null, ref salt, IntPtr.Zero, IntPtr.Zero, flags, out result)
                : CryptUnprotectData(ref data, IntPtr.Zero, ref salt, IntPtr.Zero, IntPtr.Zero, flags, out result);
            if (!ok) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
            var bytes = new byte[result.Length];
            Marshal.Copy(result.Data, bytes, 0, bytes.Length);
            return bytes;
        }
        finally { if (result.Data != IntPtr.Zero) LocalFree(result.Data); b.Free(); a.Free(); }
    }
}
