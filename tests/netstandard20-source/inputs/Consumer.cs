using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

public static class StandardConsumer
{
    public static async Task<string> Run()
    {
        var names = new Dictionary<string,int> { ["Grüße 世界"] = 3 };
        using (var stream = new MemoryStream())
        {
            byte[] data=Encoding.UTF8.GetBytes(names.Keys.Single());
            await stream.WriteAsync(data,0,data.Length);
            stream.Position=0;
            using (var reader=new StreamReader(stream,Encoding.UTF8))
                return (await reader.ReadToEndAsync())+":"+Enumerable.Range(1,4).Sum()+":"+(1,"tuple").Item2;
        }
    }
}
