// Read-only real Windows SQL Server gate. Settings stay outside the repository.
using System;
using System.Data.SqlClient;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using System.Security.Cryptography;
using System.Text;

static class RealLpc
{
    static async Task<int> Main(string[] args)
    {
        try
        {
            string client=typeof(SqlConnection).Assembly.Location;
            if(!Path.GetFullPath(client).StartsWith(Path.GetFullPath(AppContext.BaseDirectory),StringComparison.OrdinalIgnoreCase)||!client.Replace('\\','/').Contains("/runtimes/win/lib/net8.0/",StringComparison.Ordinal))throw new InvalidOperationException("Restored Windows source implementation required");
            using(var process=System.Diagnostics.Process.GetCurrentProcess())
                foreach(System.Diagnostics.ProcessModule module in process.Modules)
                    if(module.ModuleName.Equals("sni.dll",StringComparison.OrdinalIgnoreCase)||module.FileName.Contains(@"\Microsoft.NET\Framework",StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("Proprietary SNI/Framework fallback");
            using var input=JsonDocument.Parse(File.ReadAllText(args[0]));var settings=input.RootElement;
            string server=settings.GetProperty("server").GetString();
            if(!server.StartsWith("lpc:",StringComparison.OrdinalIgnoreCase))throw new ArgumentException("Explicit LPC server required");
            bool integrated=!settings.TryGetProperty("integratedSecurity",out var security)||security.GetBoolean();
            var builder=new SqlConnectionStringBuilder{DataSource=server,InitialCatalog="master",IntegratedSecurity=integrated,ConnectTimeout=5,Pooling=false,Encrypt=settings.TryGetProperty("encrypt",out var encrypted)&&encrypted.GetBoolean(),TrustServerCertificate=settings.TryGetProperty("trustServerCertificate",out var trust)&&trust.GetBoolean()};
            if(!integrated){builder.UserID=settings.GetProperty("user").GetString();builder.Password=settings.GetProperty("password").GetString();}
            using var connection=new SqlConnection(builder.ConnectionString);await connection.OpenAsync();
            using var command=new SqlCommand("SELECT net_transport FROM sys.dm_exec_connections WHERE session_id=@@SPID",connection);
            string transport=Convert.ToString(await command.ExecuteScalarAsync());
            if(!string.Equals(transport,"Shared memory",StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("Server did not report Shared memory");
            command.CommandText="SELECT @@VERSION";string version=Convert.ToString(await command.ExecuteScalarAsync());
            if(!version.Contains("Microsoft SQL Server",StringComparison.Ordinal))throw new InvalidOperationException("Actual SQL Server required");
            File.WriteAllText(args[1],JsonSerializer.Serialize(new{passed=true,net_transport=transport,server_endpoint_sha256=Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(server))),source_client_path=typeof(SqlConnection).Assembly.Location,source_client_identity=typeof(SqlConnection).Assembly.FullName,runtime=Environment.Version.ToString(),database_modified=false},new JsonSerializerOptions{WriteIndented=true}));
            Console.WriteLine("PASS real SQL Server source-managed LPC net_transport=Shared memory");return 0;
        }
        catch(Exception error)
        {
            Console.Error.WriteLine("FAIL real LPC gate: "+error.GetType().Name+(error is SqlException sql?" Number="+sql.Number:""));return 1;
        }
    }
}
