using System;
using System.Linq;
using System.Text;
using System.Collections;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Serialization;

internal static class QualifierLookupChecks
{
    private static int checks;
    private static void Require(bool value,string message){checks++;if(!value)throw new Exception(message);}
    private static byte[] Bytes(string value)=>Encoding.Unicode.GetPreamble().Concat(Encoding.Unicode.GetBytes(value)).ToArray();
    private static int Main(string[] args)
    {
        try
        {
            bool baseline=args.Contains("--baseline");
            using var reader=CimMofDeserializer.Create();uint offset=0;
            using var cls=reader.DeserializeClasses(Bytes("class MSYS2_QualifierLookup { [Description(\"expected 雪\"), Static] uint32 Echo([In,Description(\"input\")] uint32 Input); [Description(\"other\")] uint32 Other(); };"),ref offset).Single();
            var method=cls.CimClassMethods["Echo"];
            var enumerated=method.Qualifiers.Single(q=>q.Name=="Description");
            var named=method.Qualifiers["Description"];
            Console.WriteLine("LOOKUP method=Echo enumerated="+enumerated.Name+" value="+enumerated.Value+" named="+(named?.Name??"null"));
            Require((string)enumerated.Value=="expected 雪","Native method qualifier exists and enumerates");
            if(baseline)
            {
                Require(named==null,"Installed baseline uses method name instead of qualifier lookup name");
                Console.WriteLine("REPRODUCED method qualifier enumeration succeeds but named lookup returns null");
            }
            else
            {
                foreach(var item in cls.CimClassMethods)
                {
                    foreach(var qualifier in item.Qualifiers)
                    {
                        var found=item.Qualifiers[qualifier.Name];
                        Require(found!=null&&found.Name==qualifier.Name,"Named method qualifier agrees with enumeration");
                        Require(StructuralComparisons.StructuralEqualityComparer.Equals(found.Value,qualifier.Value)&&found.CimType==qualifier.CimType&&found.Flags==qualifier.Flags,"Named qualifier value/type/flags");
                    }
                    Require(item.Qualifiers["MSYS2_Missing"]==null,"Unknown qualifier returns null");
                }
                Require((string)method.Parameters["Input"].Qualifiers["Description"].Value=="input","Parameter qualifier named lookup remains valid");
                using var session=CimSession.Create(null);
                using var live=session.GetClass("root/cimv2","Win32_Process");
                int liveQualifiers=0;
                foreach(var liveMethod in live.CimClassMethods)
                {
                    foreach(var qualifier in liveMethod.Qualifiers)
                    {
                        var found=liveMethod.Qualifiers[qualifier.Name];liveQualifiers++;
                        Require(found!=null&&found.Name==qualifier.Name,"Live named method qualifier agrees with enumeration");
                        Require(StructuralComparisons.StructuralEqualityComparer.Equals(found.Value,qualifier.Value)&&found.CimType==qualifier.CimType&&found.Flags==qualifier.Flags,"Live native qualifier value/type/flags, including arrays");
                    }
                    Require(liveMethod.Qualifiers["MSYS2_Missing"]==null,"Unknown live qualifier returns null");
                }
                Require(liveQualifiers>0,"Live Windows provider method qualifiers exercised");
                Console.WriteLine("LIVE_METHOD_QUALIFIERS "+liveQualifiers);
            }
            Console.WriteLine("PASS "+checks+" method qualifier lookup checks"+(baseline?" (baseline reproduction)":""));return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
}
