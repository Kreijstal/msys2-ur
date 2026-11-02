using System;
using System.IO;
using System.Linq;
using System.Numerics;
using Assimp;
using Assimp.Unmanaged;
class Check {
const string Obj="mtllib tri.mtl\no Triangle\nv 0 0 0\nv 1 0 0\nv 0 2 0\nv 0 0 3\nvn 0 0 1\nusemtl red\nf 1//1 2//1 3//1\nf 1//1 3//1 4//1\n";
const string Mtl="newmtl red\nKd 1.0 0.25 0.0\n";
static void Main(string[] args){
var expectedBin=Path.GetFullPath(args[0]);
var asm=typeof(AssimpContext).Assembly.GetName();
var token=Convert.ToHexString(asm.GetPublicKeyToken()!).ToLowerInvariant();
if(asm.Name!="AssimpNetter"||asm.Version!=new Version(6,0,5,0)||token!="0d51b391f59f42a6")throw new Exception("strong-name identity "+asm.FullName);
if(Directory.EnumerateFiles(AppContext.BaseDirectory,"*",SearchOption.AllDirectories).Select(Path.GetFileName).Any(f=>f!.Equals("assimp.dll",StringComparison.OrdinalIgnoreCase)||f.StartsWith("libassimp",StringComparison.OrdinalIgnoreCase)))throw new Exception("a native assimp binary was copied next to the app");
var dir=Path.Combine(Path.GetTempPath(),"assimpnetter-check-"+Environment.ProcessId);Directory.CreateDirectory(dir);
try{
 File.WriteAllText(Path.Combine(dir,"tri.obj"),Obj);File.WriteAllText(Path.Combine(dir,"tri.mtl"),Mtl);
 using var ctx=new AssimpContext();
 var scene=ctx.ImportFile(Path.Combine(dir,"tri.obj"),PostProcessSteps.Triangulate|PostProcessSteps.JoinIdenticalVertices);
 var lib=AssimpLibrary.Instance;
 Console.WriteLine($"  native library: {lib.LibraryPath} (assimp {lib.GetVersion()})");
 if(!Path.IsPathRooted(lib.LibraryPath)||!string.Equals(Path.GetDirectoryName(Path.GetFullPath(lib.LibraryPath)),expectedBin.TrimEnd('\\','/'),StringComparison.OrdinalIgnoreCase)||!string.Equals(Path.GetFileName(lib.LibraryPath),"libassimp-6.dll",StringComparison.OrdinalIgnoreCase))
  throw new Exception("native library not resolved from $MINGW_PREFIX/bin via the runtime directory: "+lib.LibraryPath);
 if(lib.GetVersionMajor()!=6)throw new Exception("native assimp version "+lib.GetVersion());
 if(scene==null||scene.MeshCount!=1)throw new Exception("mesh count "+scene?.MeshCount);
 var mesh=scene.Meshes[0];
 if(mesh.VertexCount!=4||mesh.FaceCount!=2||mesh.Faces.Any(f=>f.IndexCount!=3))throw new Exception($"mesh topology {mesh.VertexCount} vertices {mesh.FaceCount} faces");
 var pts=mesh.Vertices.OrderBy(v=>v.X).ThenBy(v=>v.Y).ThenBy(v=>v.Z).ToArray();
 if(!pts.SequenceEqual(new[]{new Vector3(0,0,0),new Vector3(0,0,3),new Vector3(0,2,0),new Vector3(1,0,0)}))throw new Exception("vertex positions "+string.Join(" ",pts));
 if(!mesh.HasNormals||mesh.Normals.Any(n=>n!=new Vector3(0,0,1)))throw new Exception("normals");
 var mat=scene.Materials[mesh.MaterialIndex];
 if(!mat.HasColorDiffuse||Vector4.Distance(mat.ColorDiffuse,new Vector4(1,0.25f,0,1))>1e-5)throw new Exception("material diffuse "+mat.ColorDiffuse);
 // Export to binary glTF2 in memory and import it back from a stream
 var blob=ctx.ExportToBlob(scene,"glb2");
 if(blob==null||!blob.HasData)throw new Exception("GLB export");
 var again=ctx.ImportFileFromStream(new MemoryStream(blob.Data),PostProcessSteps.None,"glb");
 if(again.MeshCount!=1||again.Meshes[0].FaceCount!=2)throw new Exception("GLB re-import");
 Console.WriteLine($"  imported OBJ: 1 mesh, {mesh.VertexCount} vertices, {mesh.FaceCount} faces, diffuse {mat.ColorDiffuse}; GLB blob {blob.Data.Length} bytes re-imported");
}finally{Directory.Delete(dir,true);}
Console.WriteLine("PASS AssimpNetter "+asm.Version+" strong-named token "+token+"; MSYS2 libassimp-6.dll loaded by full path from $MINGW_PREFIX/bin derived from the runtime directory, OBJ+MTL import (positions/normals/material), binary glTF2 export/re-import from a stream");}}
