// Exercise the Release source port against the original upstream TDS peer.
// This peer is a protocol fixture, not an actual SQL Server database engine.
using System;
using System.Collections.Generic;
using System.Data.SqlClient;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Security.Principal;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SqlServer.TDS.EndPoint;
using Microsoft.SqlServer.TDS;
using Microsoft.SqlServer.TDS.PreLogin;
using Microsoft.SqlServer.TDS.Servers;

static class SourceSniProbe
{
    static void Require(bool value, string message)
    { if (!value) throw new Exception(message); }

    static void CheckNativeModules()
    {
        var paths = new List<string>();
        foreach (ProcessModule module in Process.GetCurrentProcess().Modules)
        {
            Require(!module.ModuleName.Equals("sni.dll", StringComparison.OrdinalIgnoreCase), "no prebuilt sni.dll");
            Require(!module.FileName.Contains(@"\Microsoft.NET\Framework", StringComparison.OrdinalIgnoreCase),
                "no Framework implementation: " + module.FileName);
            paths.Add(module.FileName);
        }
        paths.Sort(StringComparer.OrdinalIgnoreCase);
        File.WriteAllLines("loaded-modules.txt", paths);
        Console.WriteLine("PASS recorded native module paths; no sni.dll or Framework implementation");
    }

    sealed class ObservedServer : GenericTDSServer
    {
        public string AuthenticatedIdentity;
        public ObservedServer(TDSServerArguments arguments) : base(arguments) { }
        protected override TDSMessageCollection OnAuthenticationCompleted(ITDSServerSession session)
        {
            if (session.NTUserAuthenticationContext != null)
            {
                using var identity = (WindowsIdentity)session.NTUserAuthenticationContext.GetRemoteIdentity();
                Require(identity.IsAuthenticated, "server SSPI context has an authenticated identity");
                AuthenticatedIdentity = identity.Name;
            }
            return base.OnAuthenticationCompleted(session);
        }
    }

    // Adapt a private named pipe to the unchanged upstream TCP endpoint. This
    // forwards bytes; it does not implement login, TLS, SSPI or query responses.
    sealed class PipeBridge : IDisposable
    {
        readonly NamedPipeServerStream pipe;
        readonly TcpClient socket = new TcpClient();
        readonly CancellationTokenSource cancel = new CancellationTokenSource();
        public readonly string DataSource;
        readonly Task pump;
        public PipeBridge(int port, bool shortPipe)
        {
            string name = "SqlClientSource_" + Guid.NewGuid().ToString("N") + (shortPipe ? "" : @"\sql\query");
            DataSource = @"np:\\.\pipe\" + name;
            pipe = new NamedPipeServerStream(name, PipeDirection.InOut, 1,
                PipeTransmissionMode.Byte, PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly);
            pump = Run(port);
        }
        async Task Run(int port)
        {
            try
            {
                await pipe.WaitForConnectionAsync(cancel.Token);
                await socket.ConnectAsync(IPAddress.Loopback, port, cancel.Token);
                using var stream = socket.GetStream();
                Task outgoing = pipe.CopyToAsync(stream, cancel.Token);
                Task incoming = stream.CopyToAsync(pipe, cancel.Token);
                await Task.WhenAny(outgoing, incoming);
                cancel.Cancel();
                await Task.WhenAll(outgoing, incoming);
            }
            catch (OperationCanceledException) when (cancel.IsCancellationRequested) { }
            catch (IOException) when (cancel.IsCancellationRequested) { }
        }
        public void Dispose()
        {
            cancel.Cancel(); pipe.Dispose(); socket.Dispose();
            try { pump.GetAwaiter().GetResult(); }
            catch (ObjectDisposedException) when (cancel.IsCancellationRequested) { }
            cancel.Dispose();
        }
    }

    static async Task Scenario(TDSPreLoginTokenEncryptionType encryption, bool encrypt, bool trust, bool integrated, bool namedPipe, bool shortPipe)
    {
        var arguments = new TDSServerArguments { Encryption = encryption };
        var server = new ObservedServer(arguments);
        var endpoint = new TDSServerEndPoint(server) {
            ServerEndPoint = new IPEndPoint(IPAddress.Loopback, 0), EventLog = Console.Out,
            EndpointName = $"pipe={namedPipe}/short={shortPipe}/TLS={encryption}/encrypt={encrypt}/trust={trust}/SSPI={integrated}"
        };
        endpoint.Start();
        try
        {
            using var bridge = namedPipe ? new PipeBridge(endpoint.ServerEndPoint.Port, shortPipe) : null;
            var builder = new SqlConnectionStringBuilder {
                DataSource = namedPipe ? bridge.DataSource : "tcp:localhost," + endpoint.ServerEndPoint.Port,
                Encrypt = encrypt, TrustServerCertificate = trust, IntegratedSecurity = integrated,
                Pooling = false, ConnectTimeout = 5
            };
            if (!integrated) { builder.UserID = "fixture"; builder.Password = "fixture"; }
            using var connection = new SqlConnection(builder.ConnectionString);
            bool reject = encrypt && !trust;
            try { await connection.OpenAsync(); }
            catch (SqlException e) when (reject)
            {
                // Require a TLS/certificate failure, not a transport timeout or
                // another failure that would hide broken validation behavior.
                string text = e.ToString();
                Require(text.Contains("SSL", StringComparison.OrdinalIgnoreCase) &&
                    (text.Contains("certificate", StringComparison.OrdinalIgnoreCase) ||
                     text.Contains("AuthenticationException", StringComparison.Ordinal)), text);
                Console.WriteLine("PASS untrusted owned certificate rejected with TrustServerCertificate=false");
                return;
            }
            Require(!reject, "untrusted certificate must not be accepted");
            using var command = connection.CreateCommand();
            command.CommandText = "SELECT TOP (1) [encrypt_option] FROM [sys].[dm_exec_connections] WHERE [session_id] = @@SPID";
            string expected = encrypt || encryption == TDSPreLoginTokenEncryptionType.Required ? "TRUE" : "FALSE";
            Require((string)command.ExecuteScalar() == expected, "synchronous server-observed encryption state");
            using (var reader = await command.ExecuteReaderAsync())
            {
                Require(await reader.ReadAsync() && reader.GetString(0) == expected && reader.GetName(0) == "encrypt_option", "async encryption row/metadata");
                Require(!await reader.ReadAsync(), "async DONE");
            }
            if (integrated)
            {
                command.CommandText = "SELECT TOP (1) [auth_scheme] FROM [sys].[dm_exec_connections] WHERE [session_id] = @@SPID";
                string scheme = Convert.ToString(await command.ExecuteScalarAsync());
                // The unchanged upstream QueryEngine spells this marker NTML.
                // Its server performs real SSPI before completing this login;
                // the marker alone does not identify NTLM versus Kerberos.
                Require(scheme == "NTML", "upstream integrated-authentication marker: " + scheme);
                using var current = WindowsIdentity.GetCurrent();
                Require(string.Equals(server.AuthenticatedIdentity, current.Name, StringComparison.OrdinalIgnoreCase),
                    "server SSPI identity agrees with current Windows identity");
                Console.WriteLine("PASS Windows integrated login: upstream native SSPI context authenticates current user; marker=" + scheme);
            }
            Console.WriteLine("PASS Release SNI upstream peer " + endpoint.EndpointName + ": sync/async rows, schema, DONE; encryption=" + expected);
        }
        finally { endpoint.Stop(); arguments.EncryptionCertificate.Dispose(); }
    }

    static async Task Main(string[] args)
    {
        Require(Environment.GetEnvironmentVariable("System.Data.SqlClient.UseManagedSNIOnWindows") == null,
            "Release port must run without the upstream Debug environment switch");
        var assembly = typeof(SqlConnection).Assembly;
        var factory = assembly.GetType("System.Data.SqlClient.TdsParserStateObjectFactory", true);
        Require((bool)factory.GetProperty("UseManagedSNI", BindingFlags.Public|BindingFlags.Static).GetValue(null), "Release factory selects source-managed SNI");
        if (args.Length == 1 && args[0] == "--mars-window-only")
        {
            await MarsWindowProbe.Run();
            CheckNativeModules();
            return;
        }
        if (args.Length == 1 && args[0] == "--mars-only")
        {
            await MarsTdsProbe.Run();
            await MarsWindowProbe.Run();
            CheckNativeModules();
            return;
        }
        Require(args.Length == 0, "unknown probe arguments");
        using var key = RSA.Create(2048);
        var request = new CertificateRequest("CN=localhost", key, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        var san = new SubjectAlternativeNameBuilder(); san.AddDnsName("localhost");
        request.CertificateExtensions.Add(san.Build());
        request.CertificateExtensions.Add(new X509BasicConstraintsExtension(false, false, 0, true));
        var usages = new OidCollection { new Oid("1.3.6.1.5.5.7.3.1") };
        request.CertificateExtensions.Add(new X509EnhancedKeyUsageExtension(usages, true));
        using var certificate = request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-1), DateTimeOffset.UtcNow.AddHours(1));
        // Original TDSServerArguments loads this filename and password. This
        // replaces its binary fixture with an owned in-memory generated key.
        const string path = "TdsServerCertificate.pfx";
        Require(!File.Exists(path), "owned certificate path must be new");
        File.WriteAllBytes(path, certificate.Export(X509ContentType.Pfx, "PLACEHOLDER"));
        try
        {
            foreach (int transport in new[] { 0, 1, 2 })
            {
                bool namedPipe = transport != 0, shortPipe = transport == 2;
                await Scenario(TDSPreLoginTokenEncryptionType.NotSupported, false, false, false, namedPipe, shortPipe);
                await Scenario(TDSPreLoginTokenEncryptionType.On, true, true, false, namedPipe, shortPipe);
                await Scenario(TDSPreLoginTokenEncryptionType.Required, false, true, false, namedPipe, shortPipe);
                await Scenario(TDSPreLoginTokenEncryptionType.On, true, false, false, namedPipe, shortPipe);
                await Scenario(TDSPreLoginTokenEncryptionType.NotSupported, false, false, true, namedPipe, shortPipe);
                await Scenario(TDSPreLoginTokenEncryptionType.On, true, true, true, namedPipe, shortPipe);
            }
            await MarsTdsProbe.Run();
            await MarsWindowProbe.Run();
            CheckNativeModules();
            Console.WriteLine("PASS Release source-managed SNI: original upstream TDS peer, TLS/certificate policies, Windows SSPI; no sni.dll");
        }
        finally { File.Delete(path); }
    }
}
