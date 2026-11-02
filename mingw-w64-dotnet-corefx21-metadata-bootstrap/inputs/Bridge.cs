using System;
using System.Collections.Immutable;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using System.Threading.Tasks;

public static class Bridge
{
    static void Require(bool value,string name) {if(!value)throw new Exception(name);}
    public static string Run()
    {
        Require(typeof(ImmutableArray).Assembly.GetName().Version.ToString()=="1.2.3.0","Must execute Immutable1.5");
        Require(typeof(PEReader).Assembly.GetName().Version.ToString()=="1.4.3.0","Must execute Metadata1.6");
        var array=ImmutableArray.Create(1,2,3);var changed=array.SetItem(0,42);
        Require(array[0]==1 && changed[0]==42 && array.ItemRef(1)==2,"Array persistence/ref API");
        var builder=array.ToBuilder();builder.Add(4);Require(builder.ToImmutable().SequenceEqual(new[]{1,2,3,4}),"Array builder");
        var dictionary=ImmutableDictionary.Create<string,int>(StringComparer.OrdinalIgnoreCase).Add("Key",1);
        Require(dictionary["KEY"]==1 && dictionary.SetItem("key",2)["KEY"]==2 && dictionary["key"]==1,"Dictionary comparer/persistence");
        var list=ImmutableList.CreateRange(Enumerable.Range(0,100));
        Require(list.RemoveRange(10,80).Count==20 && list.Count==100 && list.Reverse()[0]==99,"List tree edits");
        Require(ImmutableHashSet.Create(1,2,3).SymmetricExcept(new[]{2,4}).SetEquals(new[]{1,3,4}),"Hash set");
        Require(ImmutableSortedSet.Create(3,1,2).SequenceEqual(new[]{1,2,3}),"Sorted set");
        Require(ImmutableSortedDictionary<int,string>.Empty.Add(2,"b").Add(1,"a").Keys.SequenceEqual(new[]{1,2}),"Sorted dictionary");
        Require(ImmutableQueue<int>.Empty.Enqueue(1).Enqueue(2).Dequeue().Peek()==2,"Queue");
        Require(ImmutableStack<int>.Empty.Push(1).Push(2).Pop().Peek()==1,"Stack");
        var atomic=ImmutableDictionary<int,int>.Empty;
        Parallel.For(0,100,i=>ImmutableInterlocked.TryAdd(ref atomic,i,i*i));
        Require(atomic.Count==100 && atomic[9]==81,"Interlocked concurrent publication");
        bool invalid=false;try {array.SetItem(99,0);}catch(ArgumentOutOfRangeException e){invalid=!string.IsNullOrEmpty(e.Message);}
        Require(invalid,"Array negative bounds/resource message");

        var metadata=new MetadataBuilder();var mvid=Guid.Parse("11223344-5566-7788-99aa-bbccddeeff00");
        metadata.AddModule(0,metadata.GetOrAddString("Owned.dll"),metadata.GetOrAddGuid(mvid),default(GuidHandle),default(GuidHandle));
        metadata.AddAssembly(metadata.GetOrAddString("Owned_✓"),new Version(1,2,3,4),default(StringHandle),default(BlobHandle),0,AssemblyHashAlgorithm.None);
        metadata.AddTypeDefinition(TypeAttributes.NotPublic,default(StringHandle),metadata.GetOrAddString("<Module>"),default(EntityHandle),MetadataTokens.FieldDefinitionHandle(1),MetadataTokens.MethodDefinitionHandle(1));
        var peBuilder=new ManagedPEBuilder(PEHeaderBuilder.CreateLibraryHeader(),new MetadataRootBuilder(metadata),new BlobBuilder());
        var image=new BlobBuilder();peBuilder.Serialize(image);
        using(var pe=new PEReader(new MemoryStream(image.ToArray())))
        {
            var reader=pe.GetMetadataReader();
            Require(reader.GetString(reader.GetAssemblyDefinition().Name)=="Owned_✓" && reader.GetGuid(reader.GetModuleDefinition().Mvid)==mvid,"PE write/read Unicode/MVID");
            Require(reader.TypeDefinitions.Count==1 && pe.HasMetadata,"Metadata row tables");
        }
        using(var own=new PEReader(File.OpenRead(typeof(Bridge).Assembly.Location)))
        {
            var reader=own.GetMetadataReader();
            Require(reader.MethodDefinitions.Count>=2 && reader.GetString(reader.GetAssemblyDefinition().Name)=="Bridge","Actual consumer PE metadata");
        }
        var pdbMetadata=new MetadataBuilder();
        var document=pdbMetadata.AddDocument(pdbMetadata.GetOrAddDocumentName("owned/✓.cs"),default(GuidHandle),default(BlobHandle),default(GuidHandle));
        var pdb=new PortablePdbBuilder(pdbMetadata,ImmutableArray.Create(new int[64]),default(MethodDefinitionHandle));
        var pdbImage=new BlobBuilder();pdb.Serialize(pdbImage);
        using(var provider=MetadataReaderProvider.FromPortablePdbImage(ImmutableArray.Create(pdbImage.ToArray())))
        {
            var reader=provider.GetMetadataReader();Require(reader.GetString(reader.GetDocument(document).Name)=="owned/✓.cs","Portable PDB document round trip");
        }
        invalid=false;try{new PEReader(new MemoryStream(new byte[]{0,1,2,3})).GetMetadataReader();}catch(BadImageFormatException){invalid=true;}
        Require(invalid,"Malformed PE negative control");
        return "PASS original Immutable1.5 collection families/ref API/concurrency and Metadata1.6 PE/portable-PDB readers/writers/negative controls";
    }
}
