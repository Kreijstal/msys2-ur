using System;
using System.IO;
using System.Linq;
using NVorbis;
class Check {
// Reference values from an independent decoder (FFmpeg's native Vorbis decoder, f32 output) over upstream's TestFiles.
static readonly (string file,int rate,int channels,long frames,double rms)[] Files={
 ("1test.ogg",44100,1,17190,0.006623),("2test.ogg",44100,1,315790,0.171086),
 ("3test.ogg",44100,2,288094,0.126417),("issue6test.ogg",44100,2,548160,0.253134)};
static readonly float[] Window2={-0.222673f,-0.225476f,-0.228117f,-0.230594f,-0.232905f,-0.235050f,-0.237026f,-0.238831f,-0.240466f,-0.241927f,-0.243215f,-0.244328f,-0.245266f,-0.246028f,-0.246612f,-0.247020f};
static void Main(string[] args){
var dir=args[0];var asm=typeof(VorbisReader).Assembly.GetName();
if(asm.Name!="NVorbis"||asm.Version!=new Version(0,10,4,0))throw new Exception("assembly identity "+asm.FullName);
foreach(var f in Files){
 using var r=new VorbisReader(Path.Combine(dir,f.file));r.ClipSamples=false;
 if(r.SampleRate!=f.rate||r.Channels!=f.channels)throw new Exception(f.file+" header "+r.SampleRate+"/"+r.Channels);
 if(string.IsNullOrEmpty(r.Tags.EncoderVendor)||!r.Tags.EncoderVendor.StartsWith("Xiph.Org libVorbis"))throw new Exception(f.file+" vendor "+r.Tags.EncoderVendor);
 var buf=new float[4096*f.channels];long n=0;double sq=0;int got;
 long limit=f.frames*f.channels;
 while((got=r.ReadSamples(buf,0,buf.Length))>0){for(int i=0;i<got;i++)if(n+i<limit)sq+=buf[i]*(double)buf[i];n+=got;}
 long frames=n/f.channels;double rms=Math.Sqrt(sq/limit);
 // NVorbis 0.10.4 does not apply end-of-stream granule trimming to every file, so it may return up to one long block of trailing padding.
 if(frames<f.frames||frames-f.frames>2048)throw new Exception(f.file+" decoded "+frames+" frames, reference "+f.frames);
 if(Math.Abs(rms-f.rms)>f.rms*0.001+1e-6)throw new Exception(f.file+" rms "+rms+" reference "+f.rms);
 Console.WriteLine($"  {f.file}: {f.channels}ch {f.rate}Hz {frames} frames rms {rms:F6} (ref {f.rms:F6})");}
using(var r=new VorbisReader(Path.Combine(dir,"2test.ogg"))){
 r.SeekTo(100000);var w=new float[16];if(r.ReadSamples(w,0,16)!=16)throw new Exception("short read after seek");
 var err=w.Zip(Window2,(a,b)=>Math.Abs(a-b)).Max();if(err>2e-3)throw new Exception("seeked sample window differs from reference by "+err);
 Console.WriteLine($"  2test.ogg seek to 100000: max |err| {err:E2} over 16 samples");}
Console.WriteLine("PASS NVorbis "+asm.Version+"; decoded 4 upstream Ogg Vorbis files (mono/stereo, libVorbis 1.0-1.3.5) matching FFmpeg frame counts (within end padding) and RMS (0.1%), sample-accurate seek");}}
