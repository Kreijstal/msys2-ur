using System;
using System.Collections.Generic;
using System.Data;
using System.Data.SqlClient;
using System.Data.SqlTypes;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

static class FileStreamGate
{
    static readonly List<string> Checks = new();
    static void Require(bool condition, string name)
    {
        if (!condition) throw new InvalidOperationException(name);
        Checks.Add(name);
    }

    static string Setting(JsonElement settings, string name)
    {
        string value = settings.GetProperty(name).GetString() ?? "";
        if (string.IsNullOrWhiteSpace(value)) throw new ArgumentException("Required nonempty setting: " + name);
        return value;
    }

    static SqlConnectionStringBuilder Connection(JsonElement settings)
    {
        if (!settings.GetProperty("integratedSecurity").GetBoolean())
            throw new ArgumentException("FILESTREAM requires Windows integrated security");
        if (settings.TryGetProperty("user", out _) || settings.TryGetProperty("password", out _))
            throw new ArgumentException("SQL credentials are not accepted by this Windows FILESTREAM gate");
        return new SqlConnectionStringBuilder {
            DataSource = Setting(settings, "server"), InitialCatalog = Setting(settings, "database"),
            IntegratedSecurity = true, Pooling = false, ConnectTimeout = 8,
            Encrypt = !settings.TryGetProperty("encrypt", out var encrypt) || encrypt.GetBoolean(),
            TrustServerCertificate = settings.TryGetProperty("trustServerCertificate", out var trust) && trust.GetBoolean(),
            ApplicationName = "Owned source SqlFileStream gate"
        };
    }

    static object Scalar(SqlConnection connection, string text, SqlTransaction? transaction = null)
    {
        using var command = new SqlCommand(text, connection, transaction) { CommandTimeout = 15 };
        return command.ExecuteScalar() ?? DBNull.Value;
    }

    static void Execute(SqlConnection connection, string text, SqlTransaction? transaction = null)
    {
        using var command = new SqlCommand(text, connection, transaction) { CommandTimeout = 15 };
        command.ExecuteNonQuery();
    }

    static (string Path, byte[] Context) Context(SqlConnection connection, SqlTransaction transaction, string table)
    {
        using var command = new SqlCommand("SELECT Payload.PathName(), GET_FILESTREAM_TRANSACTION_CONTEXT() FROM " + table + " WHERE Id=1", connection, transaction);
        using var reader = command.ExecuteReader();
        Require(reader.Read(), "Owned FILESTREAM row found");
        string path = reader.GetString(0);
        byte[] context = (byte[])reader.GetValue(1);
        Require(path.StartsWith(@"\\", StringComparison.Ordinal) && context.Length > 0, "Native path and explicit transaction context returned");
        return (path, context);
    }

    static byte[] StreamRead(string path, byte[] context)
    {
        using var stream = new SqlFileStream(path, context, FileAccess.Read, FileOptions.SequentialScan, 0);
        using var copy = new MemoryStream();
        stream.CopyTo(copy);
        return copy.ToArray();
    }

    static void ValidateSource()
    {
        string path = typeof(SqlFileStream).Assembly.Location;
        Require(typeof(SqlFileStream).Assembly == typeof(SqlConnection).Assembly, "Stream and connection use the same source SqlClient assembly");
        Require(path.Replace('\\', '/').Contains("/runtimes/win/lib/net8.0/System.Data.SqlClient.dll", StringComparison.Ordinal), "Restored Windows implementation selected");
        using var process = Process.GetCurrentProcess();
        foreach (ProcessModule module in process.Modules)
            if (module.ModuleName.Equals("sni.dll", StringComparison.OrdinalIgnoreCase) ||
                module.FileName.Contains(@"\Microsoft.NET\Framework", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Proprietary SNI or Framework fallback");
    }

    static void SelfCheck(string output)
    {
        using var valid = JsonDocument.Parse("{\"server\":\"dummy.invalid\",\"database\":\"Owned\",\"integratedSecurity\":true}");
        var builder = Connection(valid.RootElement);
        Require(builder.IntegratedSecurity && builder.Encrypt && !builder.TrustServerCertificate && !builder.Pooling,
            "Offline settings retain integrated authentication, TLS checks and no pooling");
        foreach (string invalid in new[] {
            "{\"server\":\"dummy.invalid\",\"database\":\"Owned\",\"integratedSecurity\":false}",
            "{\"server\":\"dummy.invalid\",\"database\":\"Owned\",\"integratedSecurity\":true,\"password\":\"dummy\"}",
            "{\"server\":\"dummy.invalid\",\"database\":\"\",\"integratedSecurity\":true}" })
        {
            using var document = JsonDocument.Parse(invalid);
            bool rejected = false;
            try { _ = Connection(document.RootElement); }
            catch (ArgumentException) { rejected = true; }
            Require(rejected, "Invalid offline settings rejected");
        }
        File.WriteAllText(output, JsonSerializer.Serialize(new {
            preparation_passed = true, assertions = Checks.Count, checks = Checks,
            server_connection_attempted = false, FILESTREAM_interoperability_verified = false
        }, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine("PASS " + Checks.Count + " offline FILESTREAM preparation checks; no connection attempted");
    }

    static void Live(JsonElement settings, string output)
    {
        var builder = Connection(settings);
        string table = "dbo.[CodexFileStream_" + Guid.NewGuid().ToString("N") + "]";
        byte[] seed = Encoding.UTF8.GetBytes("owned FILESTREAM seed € 雪");
        byte[] payload = Enumerable.Range(0, 131073).Select(i => (byte)(i * 37)).ToArray();
        byte[] appended = payload.Concat(new byte[] { 0, 255, 42 }).ToArray();
        using var connection = new SqlConnection(builder.ConnectionString);
        connection.Open();
        Require(Convert.ToString(Scalar(connection, "SELECT @@VERSION"))!.Contains("Microsoft SQL Server", StringComparison.Ordinal), "Actual SQL Server engine");
        Require(Convert.ToInt32(Scalar(connection, "SELECT SERVERPROPERTY('FilestreamEffectiveLevel')")) >= 2, "FILESTREAM streaming already enabled");
        object selectedGroup = Scalar(connection, "SELECT TOP (1) name FROM sys.filegroups WHERE type='FD' AND is_read_only=0 ORDER BY is_default DESC, data_space_id");
        Require(selectedGroup is string group && !string.IsNullOrWhiteSpace(group), "Selected database already has a writable FILESTREAM filegroup");
        string filegroup = "[" + ((string)selectedGroup).Replace("]", "]]") + "]";
        bool created = false;
        string recovery = Path.Combine(Path.GetDirectoryName(Path.GetFullPath(output))!, "owned-table-recovery.json");
        File.WriteAllText(recovery, JsonSerializer.Serialize(new { owned_table = table,
            action_if_interrupted = "Inspect and drop only this generated table on the authorized test database" }));
        try
        {
            Execute(connection, "CREATE TABLE " + table + " (Id int PRIMARY KEY, Token uniqueidentifier NOT NULL ROWGUIDCOL UNIQUE DEFAULT NEWID(), Payload varbinary(max) FILESTREAM NOT NULL) FILESTREAM_ON " + filegroup);
            created = true;
            using (var command = new SqlCommand("INSERT " + table + " (Id,Payload) VALUES (1,@payload)", connection))
            {
                command.Parameters.Add("@payload", SqlDbType.VarBinary, -1).Value = seed;
                command.ExecuteNonQuery();
            }
            using (var transaction = connection.BeginTransaction())
            {
                var value = Context(connection, transaction, table);
                Require(StreamRead(value.Path, value.Context).SequenceEqual(seed), "Native stream reads SQL-inserted seed");
                using (var stream = new SqlFileStream(value.Path, value.Context, FileAccess.ReadWrite, FileOptions.SequentialScan, payload.Length))
                {
                    stream.SetLength(0);
                    stream.Write(payload, 0, payload.Length);
                    stream.Flush();
                }
                transaction.Commit();
            }
            Require(Scalar(connection, "SELECT GET_FILESTREAM_TRANSACTION_CONTEXT()") == DBNull.Value, "Committed transaction has no active FILESTREAM token");
            Require(((byte[])Scalar(connection, "SELECT Payload FROM " + table + " WHERE Id=1")).SequenceEqual(payload), "Committed stream write visible through SQL");
            using (var transaction = connection.BeginTransaction())
            {
                var value = Context(connection, transaction, table);
                using (var stream = new SqlFileStream(value.Path, value.Context, FileAccess.ReadWrite, FileOptions.None, 0))
                {
                    Require(stream.Seek(0, SeekOrigin.End) == payload.Length, "Stream seek observes committed length");
                    stream.Write(new byte[] { 0, 255, 42 }, 0, 3);
                    stream.Flush();
                }
                transaction.Commit();
            }
            Require(((byte[])Scalar(connection, "SELECT Payload FROM " + table + " WHERE Id=1")).SequenceEqual(appended), "Committed append visible through SQL");
            using (var transaction = connection.BeginTransaction())
            {
                var value = Context(connection, transaction, table);
                using (var stream = new SqlFileStream(value.Path, value.Context, FileAccess.Write, FileOptions.None, 0))
                {
                    stream.SetLength(0);
                    stream.Write(seed, 0, seed.Length);
                    stream.Flush();
                }
                transaction.Rollback();
            }
            Require(Scalar(connection, "SELECT GET_FILESTREAM_TRANSACTION_CONTEXT()") == DBNull.Value, "Rolled-back transaction has no active FILESTREAM token");
            Require(((byte[])Scalar(connection, "SELECT Payload FROM " + table + " WHERE Id=1")).SequenceEqual(appended), "Rolled-back stream overwrite does not change committed data");
            using (var transaction = connection.BeginTransaction())
            {
                var value = Context(connection, transaction, table);
                Require(StreamRead(value.Path, value.Context).SequenceEqual(appended), "New native stream reads committed data after rollback");
                transaction.Commit();
            }
        }
        finally
        {
            if (created)
            {
                Execute(connection, "DROP TABLE " + table);
                Require(Scalar(connection, "SELECT OBJECT_ID(N'" + table + "')") == DBNull.Value, "Owned test table removed");
                File.Delete(recovery);
            }
        }
        ValidateSource();
        File.WriteAllText(output, JsonSerializer.Serialize(new {
            passed = true, assertions = Checks.Count, checks = Checks,
            server_endpoint_sha256 = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(builder.DataSource))),
            client_identity = typeof(SqlFileStream).Assembly.FullName,
            client_sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(typeof(SqlFileStream).Assembly.Location))),
            owned_table_removed = true, FILESTREAM_interoperability_verified = true
        }, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine("PASS " + Checks.Count + " real transactional FILESTREAM checks");
    }

    static int Main(string[] args)
    {
        try
        {
            ValidateSource();
            if (args[0] == "--self-check") SelfCheck(args[1]);
            else { using var input = JsonDocument.Parse(File.ReadAllText(args[0])); Live(input.RootElement, args[1]); }
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine("FAIL FILESTREAM gate: " + error.GetType().Name +
                (error is SqlException sql ? " Number=" + sql.Number : ""));
            return 1;
        }
    }
}
