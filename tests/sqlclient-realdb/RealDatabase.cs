using System;
using System.Collections.Generic;
using System.Data;
using System.Data.SqlClient;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

static class Program
{
    static int checks;
    static readonly List<object> results=new();
    static void Require(bool value,string message){checks++;if(!value)throw new Exception(message);}
    static SqlConnectionStringBuilder Connection(JsonElement settings,string database,bool encrypt,bool mars=false,bool trust=true)=>new()
    {
        DataSource=settings.GetProperty("server").GetString(),InitialCatalog=database,
        UserID=settings.GetProperty("user").GetString(),Password=settings.GetProperty("password").GetString(),
        IntegratedSecurity=false,Encrypt=encrypt,TrustServerCertificate=trust,
        MultipleActiveResultSets=mars,ConnectTimeout=10,Pooling=true,ApplicationName="MSYS2 SqlClient source integration"
    };
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
            using var settings=JsonDocument.Parse(File.ReadAllText(args[0]));var input=settings.RootElement;
            string clientPath=typeof(SqlConnection).Assembly.Location;Require(clientPath.Replace('\\','/').Contains("/runtimes/win/lib/net8.0/System.Data.SqlClient.dll"),"Packaged Windows implementation");
            Require(typeof(SqlConnection).Assembly.GetName().Version==new Version(4,6,1,6),"Source SqlClient identity");
            foreach(ProcessModule module in Process.GetCurrentProcess().Modules)Require(!module.ModuleName.Equals("sni.dll",StringComparison.OrdinalIgnoreCase)&&!module.FileName.Contains(@"\Microsoft.NET\Framework",StringComparison.OrdinalIgnoreCase),"Source managed transport without proprietary SNI or Framework fallback");
            using var admin=new SqlConnection(Connection(input,"master",encrypt:true).ConnectionString);await admin.OpenAsync();
            string version=Convert.ToString(Scalar(admin,"SELECT @@VERSION"))!;Require(version.Contains("Microsoft SQL Server"),"Actual SQL Server engine");
            string prefix="CodexSqlClient_"+Guid.NewGuid().ToString("N");
            foreach(bool encrypt in new[]{false,true})
            {
                string database=prefix+(encrypt?"_tls":"_plain");Execute(admin,"CREATE DATABASE ["+database+"]");
                try{await Exercise(input,database,encrypt);}
                finally{SqlConnection.ClearAllPools();Execute(admin,"ALTER DATABASE ["+database+"] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE ["+database+"]");}
            }
            bool untrustedRejected=false;try{using var untrusted=new SqlConnection(Connection(input,"master",encrypt:true,trust:false).ConnectionString);await untrusted.OpenAsync();}catch(SqlException){untrustedRejected=true;}
            Require(untrustedRejected,"Untrusted test-server certificate rejected");
            File.WriteAllText(args[1],JsonSerializer.Serialize(new{passed=true,checks,serverVersion=version,clientPath,clientIdentity=typeof(SqlConnection).Assembly.FullName,scenarios=results,LocalDB_shared_memory_FILESTREAM_verified=false},new JsonSerializerOptions{WriteIndented=true}));Console.WriteLine("PASS "+checks+" real database/source SqlClient checks");return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
}
