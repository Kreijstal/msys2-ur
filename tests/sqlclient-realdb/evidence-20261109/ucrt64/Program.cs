using System;
using System.Collections.Generic;
using System.Data;
using System.Data.SqlClient;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

static class Program
{
    static int checks;
    static readonly List<object> results=new();
    static void Require(bool value,string message){checks++;if(!value)throw new Exception(message);}
    static bool Flag(JsonElement settings,string name)=>settings.TryGetProperty(name,out var value)&&value.GetBoolean();
    static bool LocalDB(JsonElement settings)=>Flag(settings,"requireLocalDB");
    static SqlConnectionStringBuilder Connection(JsonElement settings,string database,bool encrypt,bool mars=false,bool trust=true)
    {
        string? server=settings.GetProperty("server").GetString();
        if(string.IsNullOrWhiteSpace(server))throw new ArgumentException("A server is required");
        bool integrated=Flag(settings,"integratedSecurity"),local=LocalDB(settings);
        bool localAddress=server.StartsWith(@"(localdb)\",StringComparison.OrdinalIgnoreCase)&&server.Length>10;
        if(local!=localAddress)throw new ArgumentException("LocalDB requires an explicit LocalDB address and requireLocalDB=true");
        if(local&&!integrated)throw new ArgumentException("This LocalDB gate requires Windows authentication");
        if(integrated&&(settings.TryGetProperty("user",out _)||settings.TryGetProperty("password",out _)))
            throw new ArgumentException("Do not mix Windows authentication and SQL credentials");
        var connection=new SqlConnectionStringBuilder
        {
            DataSource=server,InitialCatalog=database,IntegratedSecurity=integrated,
            Encrypt=encrypt,TrustServerCertificate=trust,MultipleActiveResultSets=mars,
            ConnectTimeout=30,Pooling=true,ApplicationName="MSYS2 SqlClient source integration"
        };
        if(!integrated)
        {
            string? user=settings.GetProperty("user").GetString(),password=settings.GetProperty("password").GetString();
            if(string.IsNullOrWhiteSpace(user)||string.IsNullOrEmpty(password))throw new ArgumentException("SQL credentials are required");
            connection.UserID=user;connection.Password=password;
        }
        return connection;
    }
    static void SelfCheck(string output)
    {
        using(var sql=JsonDocument.Parse("""{"server":"tcp:offline.invalid,1433","user":"offline","password":"offline"}"""))
        {
            var c=Connection(sql.RootElement,"master",true);
            Require(!c.IntegratedSecurity&&c.UserID=="offline"&&c.Password=="offline"&&c.Encrypt,"SQL authentication and encrypted mode preserved");
            c=Connection(sql.RootElement,"master",true,mars:true,trust:false);
            Require(c.MultipleActiveResultSets&&!c.TrustServerCertificate,"MARS and certificate validation preserved");
        }
        using(var windows=JsonDocument.Parse("""{"server":"tcp:offline.invalid,1433","integratedSecurity":true}"""))
        {
            var c=Connection(windows.RootElement,"master",true);
            Require(c.IntegratedSecurity&&c.UserID==""&&c.Password==""&&c.Encrypt,"Windows authentication without credentials");
        }
        using(var local=JsonDocument.Parse("""{"server":"(localdb)\\Offline","integratedSecurity":true,"requireLocalDB":true}"""))
        {
            var c=Connection(local.RootElement,"master",false);
            Require(LocalDB(local.RootElement)&&c.IntegratedSecurity&&!c.Encrypt&&c.DataSource==@"(localdb)\Offline","Explicit LocalDB discovery address preserved");
        }
        foreach(string invalid in new[]{
            """{"server":"","user":"u","password":"p"}""",
            """{"server":"tcp:offline.invalid","integratedSecurity":true,"user":"u"}""",
            """{"server":"tcp:offline.invalid","integratedSecurity":true,"password":"p"}""",
            """{"server":"tcp:offline.invalid","integratedSecurity":true,"requireLocalDB":true}""",
            """{"server":"(localdb)\\Offline","user":"u","password":"p","requireLocalDB":true}""",
            """{"server":"(localdb)\\Offline","integratedSecurity":true}""",
            """{"server":"(localdb)\\","integratedSecurity":true,"requireLocalDB":true}""",
            """{"server":"tcp:offline.invalid","user":"u","password":""}"""})
        {
            using var document=JsonDocument.Parse(invalid);bool rejected=false;
            try{Connection(document.RootElement,"master",false);}catch(ArgumentException){rejected=true;}
            Require(rejected,"Invalid or ambiguous offline settings rejected");
        }
        File.WriteAllText(output,JsonSerializer.Serialize(new{preparation_passed=true,assertions=checks,server_connection_attempted=false,LocalDB_interoperability_verified=false,TLS_interoperability_verified=false},new JsonSerializerOptions{WriteIndented=true}));
        Console.WriteLine("PASS "+checks+" offline source/settings checks");
    }
    static object? Scalar(SqlConnection connection,string sql,SqlTransaction? tx=null)
    {
        using var command=new SqlCommand(sql,connection,tx){CommandTimeout=10};return command.ExecuteScalar();
    }
    static void Execute(SqlConnection connection,string sql,SqlTransaction? tx=null)
    {
        using var command=new SqlCommand(sql,connection,tx){CommandTimeout=10};command.ExecuteNonQuery();
    }
    static async Task Exercise(JsonElement settings,string database,bool encrypt)
    {
        string mode=encrypt?"encrypted":"plaintext";
        using var connection=new SqlConnection(Connection(settings,database,encrypt).ConnectionString);
        await connection.OpenAsync();
        Require(connection.State==ConnectionState.Open,"Open actual database");
        string protection=Convert.ToString(Scalar(connection,"SELECT encrypt_option FROM sys.dm_exec_connections WHERE session_id=@@SPID"),CultureInfo.InvariantCulture)!;
        Require(protection==(encrypt?"TRUE":"FALSE"),"Actual SQL session encryption: "+mode);
        Execute(connection,"CREATE TABLE dbo.RoundTrip(Id int IDENTITY PRIMARY KEY,Label nvarchar(128),Amount decimal(28,9),Payload varbinary(max),Moment datetime2(7),Token uniqueidentifier,Optional nvarchar(32) NULL,Zone datetimeoffset(7))");
        string label="Å雪λ🙂'; SELECT 999;--";decimal amount=123456789012345678.123456789m;
        byte[] payload=Enumerable.Range(0,131073).Select(i=>(byte)(i*37)).ToArray();
        DateTime moment=new DateTime(2026,11,8,12,13,14,DateTimeKind.Unspecified).AddTicks(1234567);
        DateTimeOffset zone=new DateTimeOffset(moment,TimeSpan.FromMinutes(330));Guid token=Guid.Parse("1b1a711e-5e69-4e99-a363-a4a204f05601");
        using(var insert=new SqlCommand("INSERT dbo.RoundTrip(Label,Amount,Payload,Moment,Token,Optional,Zone) VALUES(@label,@amount,@payload,@moment,@token,@optional,@zone); SELECT CAST(SCOPE_IDENTITY() AS int)",connection))
        {
            insert.Parameters.Add("@label",SqlDbType.NVarChar,128).Value=label;
            var decimalParameter=insert.Parameters.Add("@amount",SqlDbType.Decimal);decimalParameter.Precision=28;decimalParameter.Scale=9;decimalParameter.Value=amount;
            insert.Parameters.Add("@payload",SqlDbType.VarBinary,-1).Value=payload;
            insert.Parameters.Add("@moment",SqlDbType.DateTime2).Value=moment;
            insert.Parameters.Add("@token",SqlDbType.UniqueIdentifier).Value=token;
            insert.Parameters.Add("@optional",SqlDbType.NVarChar,32).Value=DBNull.Value;
            insert.Parameters.Add("@zone",SqlDbType.DateTimeOffset).Value=zone;
            Require(Convert.ToInt32(await insert.ExecuteScalarAsync())==1,"Parameterized identity insert");
        }
        using(var command=new SqlCommand("SELECT Label,Amount,Payload,Moment,Token,Optional,Zone FROM dbo.RoundTrip",connection))
        using(var reader=await command.ExecuteReaderAsync(CommandBehavior.SequentialAccess))
        {
            Require(await reader.ReadAsync(),"Read typed row");Require(reader.GetString(0)==label,"Unicode and parameter quoting");Require(reader.GetDecimal(1)==amount,"Exact decimal precision");
            using(var stream=reader.GetStream(2))using(var copy=new MemoryStream()){await stream.CopyToAsync(copy);Require(copy.ToArray().SequenceEqual(payload),"Sequential binary stream");}
            Require(reader.GetDateTime(3)==moment,"datetime2 precision");Require(reader.GetGuid(4)==token,"GUID");Require(reader.IsDBNull(5),"SQL NULL");Require(reader.GetDateTimeOffset(6)==zone,"datetimeoffset precision/offset");Require(!await reader.ReadAsync(),"Exactly one row");
        }
        using(var transaction=connection.BeginTransaction(IsolationLevel.ReadCommitted))
        {
            Execute(connection,"INSERT dbo.RoundTrip(Label) VALUES(N'rolled back')",transaction);transaction.Save("source_savepoint");
            Execute(connection,"INSERT dbo.RoundTrip(Label) VALUES(N'savepoint')",transaction);transaction.Rollback("source_savepoint");
            Require(Convert.ToInt32(Scalar(connection,"SELECT COUNT(*) FROM dbo.RoundTrip",transaction))==2,"Savepoint rollback");transaction.Rollback();
        }
        Require(Convert.ToInt32(Scalar(connection,"SELECT COUNT(*) FROM dbo.RoundTrip"))==1,"Whole transaction rollback");
        using(var transaction=connection.BeginTransaction()){Execute(connection,"INSERT dbo.RoundTrip(Label) VALUES(N'committed')",transaction);transaction.Commit();}
        Require(Convert.ToInt32(Scalar(connection,"SELECT COUNT(*) FROM dbo.RoundTrip"))==2,"Transaction commit");
        Execute(connection,"CREATE TABLE dbo.BulkRows(Id int NOT NULL PRIMARY KEY,Label nvarchar(128) NOT NULL)");
        var table=new DataTable();table.Columns.Add("Id",typeof(int));table.Columns.Add("Label",typeof(string));for(int i=0;i<200;i++)table.Rows.Add(i,"row λ "+i);
        int copied=0;
        using(var bulk=new SqlBulkCopy(connection)){bulk.DestinationTableName="dbo.BulkRows";bulk.NotifyAfter=25;bulk.SqlRowsCopied+=(sender,args)=>copied=(int)args.RowsCopied;await bulk.WriteToServerAsync(table);}
        Require(copied==200&&Convert.ToInt32(Scalar(connection,"SELECT COUNT(*) FROM dbo.BulkRows"))==200,"Bulk copy and notifications");
        using(var adapter=new SqlDataAdapter("SELECT Id,Label FROM dbo.BulkRows ORDER BY Id",connection)){var data=new DataSet();Require(adapter.Fill(data)==200&&data.Tables[0].Rows[199]["Label"].Equals("row λ 199"),"DataAdapter dataset/schema");}
        using(var command=new SqlCommand("SELECT CAST(42 AS int) AS Number; SELECT N'λ' AS TextValue",connection))
        using(var reader=command.ExecuteReader())
        {
            Require(reader.Read()&&reader.GetInt32(0)==42,"First result set");Require(reader.NextResult()&&reader.Read()&&reader.GetString(0)=="λ","Second result set");Require(!reader.NextResult(),"Final DONE");
        }
        Execute(connection,"CREATE PROCEDURE dbo.SourceProcedure @value int,@doubled int OUTPUT AS BEGIN SET NOCOUNT ON; SET @doubled=@value*2; SELECT @value; RETURN 17; END");
        using(var command=new SqlCommand("dbo.SourceProcedure",connection){CommandType=CommandType.StoredProcedure})
        {
            SqlCommandBuilder.DeriveParameters(command);command.Parameters["@value"].Value=42;
            Require(Convert.ToInt32(command.ExecuteScalar())==42,"Stored procedure result");Require(Convert.ToInt32(command.Parameters["@doubled"].Value)==84,"Output parameter");Require(Convert.ToInt32(command.Parameters["@RETURN_VALUE"].Value)==17,"Return parameter");
        }
        bool serverError=false;try{Scalar(connection,"SELECT 1/0");}catch(SqlException error){serverError=error.Number==8134;}
        Require(serverError&&Convert.ToInt32(Scalar(connection,"SELECT 7"))==7,"SQL error details and connection reuse");
        using(var command=new SqlCommand("WAITFOR DELAY '00:00:05'; SELECT 1",connection){CommandTimeout=1})
        {
            bool timedOut=false;var watch=Stopwatch.StartNew();try{await command.ExecuteScalarAsync();}catch(SqlException error){timedOut=error.Number==-2;}
            Require(timedOut&&watch.Elapsed<TimeSpan.FromSeconds(5),"Real server command timeout");Require(Convert.ToInt32(Scalar(connection,"SELECT 8"))==8,"Reuse after timeout");
        }
        using(var command=new SqlCommand("WAITFOR DELAY '00:00:05'; SELECT 1",connection){CommandTimeout=10})
        using(var cancellation=new CancellationTokenSource(200))
        {
            bool canceled=false;var watch=Stopwatch.StartNew();try{await command.ExecuteScalarAsync(cancellation.Token);}catch(OperationCanceledException){canceled=true;}catch(SqlException error){canceled=cancellation.IsCancellationRequested&&error.Number==0;}
            Require(canceled&&watch.Elapsed<TimeSpan.FromSeconds(5),"Real server async cancellation");Require(Convert.ToInt32(Scalar(connection,"SELECT 9"))==9,"Reuse after cancellation");
        }
        using(var mars=new SqlConnection(Connection(settings,database,encrypt,mars:true).ConnectionString))
        {
            await mars.OpenAsync();using var first=new SqlCommand("SELECT Id FROM dbo.BulkRows ORDER BY Id",mars);using var reader=await first.ExecuteReaderAsync();Require(await reader.ReadAsync()&&reader.GetInt32(0)==0,"First MARS reader");
            using var second=new SqlCommand("SELECT SUM(Id) FROM dbo.BulkRows",mars);Require(Convert.ToInt32(await second.ExecuteScalarAsync())==19900,"Concurrent MARS command");int rows=1;while(await reader.ReadAsync())rows++;Require(rows==200,"Complete MARS reader");
        }
        results.Add(new{mode,encryption=protection,serverVersion=connection.ServerVersion,checks});Console.WriteLine("PASS real SQL Server "+mode+" parameter/transaction/bulk/MARS/error/cancellation tests");
    }
    static async Task<int> Main(string[] args)
    {
        try
        {
            if(args.Length!=2)throw new ArgumentException("Expected settings path or --self-check, and output path");
            string clientPath=typeof(SqlConnection).Assembly.Location;Require(clientPath.Replace('\\','/').Contains("/runtimes/win/lib/net8.0/System.Data.SqlClient.dll"),"Packaged Windows implementation");
            Require(typeof(SqlConnection).Assembly.GetName().Version==new Version(4,6,1,6),"Source SqlClient identity");
            foreach(ProcessModule module in Process.GetCurrentProcess().Modules)Require(!module.ModuleName.Equals("sni.dll",StringComparison.OrdinalIgnoreCase)&&!module.FileName.Contains(@"\Microsoft.NET\Framework",StringComparison.OrdinalIgnoreCase),"Source managed transport without proprietary SNI or Framework fallback");
            if(args[0]=="--self-check"){SelfCheck(args[1]);return 0;}
            using var settings=JsonDocument.Parse(File.ReadAllText(args[0]));var input=settings.RootElement;
            bool local=LocalDB(input);
            using var admin=new SqlConnection(Connection(input,"master",encrypt:!local).ConnectionString);await admin.OpenAsync();
            string version=Convert.ToString(Scalar(admin,"SELECT @@VERSION"))!;Require(version.Contains("Microsoft SQL Server"),"Actual SQL Server engine");
            object? localProperty=Scalar(admin,"SELECT SERVERPROPERTY('IsLocalDB')");
            Require(localProperty is int identity&&identity==(local?1:0),"Actual engine matches requested LocalDB/full-server identity");
            string transport=Convert.ToString(Scalar(admin,"SELECT net_transport FROM sys.dm_exec_connections WHERE session_id=@@SPID"))!;
            if(local)Require(transport.Equals("Named pipe",StringComparison.OrdinalIgnoreCase),"LocalDB discovery reaches its named pipe");
            string prefix="CodexSqlClient_"+Guid.NewGuid().ToString("N");
            foreach(bool encrypt in local?new[]{false}:new[]{false,true})
            {
                string database=prefix+(encrypt?"_tls":"_plain");Execute(admin,"CREATE DATABASE ["+database+"]");
                try{await Exercise(input,database,encrypt);}
                finally{SqlConnection.ClearAllPools();Execute(admin,"ALTER DATABASE ["+database+"] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE ["+database+"]");}
            }
            bool untrustedRejected=false;
            if(!local)
            {
                try{using var untrusted=new SqlConnection(Connection(input,"master",encrypt:true,trust:false).ConnectionString);await untrusted.OpenAsync();}catch(SqlException){untrustedRejected=true;}
                Require(untrustedRejected,"Untrusted test-server certificate rejected");
            }
            string endpointHash=Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(input.GetProperty("server").GetString()!))).ToLowerInvariant();
            File.WriteAllText(args[1],JsonSerializer.Serialize(new{passed=true,checks,serverVersion=version,endpoint_sha256=endpointHash,clientPath,clientIdentity=typeof(SqlConnection).Assembly.FullName,scenarios=results,LocalDB_verified=local,TLS_verified=!local&&untrustedRejected,shared_memory_verified=false,FILESTREAM_verified=false,transport},new JsonSerializerOptions{WriteIndented=true}));Console.WriteLine("PASS "+checks+" real database/source SqlClient checks");return 0;
        }
        catch(Exception error){Console.Error.WriteLine(JsonSerializer.Serialize(new{passed=false,errorType=error.GetType().FullName,sqlNumber=error is SqlException sql?(int?)sql.Number:null}));return 1;}
    }
}
