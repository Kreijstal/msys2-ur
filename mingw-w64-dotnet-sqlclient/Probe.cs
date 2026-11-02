using System;
using System.Data;
using System.Data.SqlClient;
using System.Data.SqlTypes;
using System.Linq;
using System.Reflection;
using Microsoft.SqlServer.Server;

static class Probe
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static int Main(string[] args)
    {
        var assembly=typeof(SqlConnection).Assembly;
        Require(assembly.GetName().Version==new Version(4,6,1,6),"upstream frozen assembly version");
        Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()=="b03f5f7f11d50a3a","upstream identity");
        Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion=="4.9.1+84b081710c66cc560b77d4de38cee493c3a38e9d","exact source version");
        assembly.GetExportedTypes();
        var builder=new SqlConnectionStringBuilder{DataSource="127.0.0.1,1",InitialCatalog="fixture;λ",UserID="fixture",Password="fixture;password",Pooling=false,ConnectTimeout=1};
        Require(new SqlConnectionStringBuilder(builder.ConnectionString).InitialCatalog=="fixture;λ","connection string escaping");
        using var connection=new SqlConnection(builder.ConnectionString);
        using var command=connection.CreateCommand();command.CommandText="select @value";
        command.Parameters.Add("@value",SqlDbType.NVarChar,100).Value="SQL λ";
        var clone=(SqlCommand)((ICloneable)command).Clone();
        using(clone){Require((string)clone.Parameters[0].Value=="SQL λ" && clone.Parameters[0].SqlDbType==SqlDbType.NVarChar,"command/parameter clone");}
        var record=new SqlDataRecord(new SqlMetaData("id",SqlDbType.Int),new SqlMetaData("text",SqlDbType.NVarChar,100));
        record.SetInt32(0,42);record.SetString(1,"record λ");
        Require(record.GetInt32(0)==42 && record.GetString(1)=="record λ" && record.GetSqlInt32(0).Value==42,"SQL record typed access");
        Console.WriteLine("PASS SqlClient source identities, exported types, connection strings, command/parameter clones and typed SQL records");
        if(args.SequenceEqual(new[]{"--no-network"}))return 0;
        Require(args.Length==0,"unknown probe arguments");
        try
        {
            connection.Open();throw new Exception("unexpected connection to fixture port");
        }
        catch(Exception error)
        {
            for(Exception cause=error;cause!=null;cause=cause.InnerException)
                if(cause is DllNotFoundException && cause.Message.Contains("sni",StringComparison.OrdinalIgnoreCase))
                {
                    Console.WriteLine("LIMITATION: unmodified Windows networking needs the unported SNI native implementation");
                    Console.WriteLine(cause.Message);return 2;
                }
            throw;
        }
    }
}
