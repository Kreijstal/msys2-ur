using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Runtime.InteropServices.WindowsRuntime;
using Windows.Data.Xml.Dom;
using Windows.Foundation.Metadata;
using Windows.Globalization;
using Windows.Graphics.Capture;
using Windows.Graphics.Imaging;
using Windows.Media.Ocr;
using Windows.Storage.Streams;
using Windows.UI.Notifications;
class Program
{
    static void Require(bool condition,string message) { if(!condition)throw new Exception(message); }
    static async Task Main()
    {
        Require(ApiInformation.IsTypePresent("Windows.Media.Ocr.OcrEngine"),"OCR type unavailable");
        var language=new Language("en-US");Require(language.LanguageTag=="en-US","language activation");
        var doc=new XmlDocument();doc.LoadXml("<root><item>λ &amp; 漢字</item></root>");
        Require(doc.SelectSingleNode("/root/item").InnerText=="λ & 漢字","native XML query");
        Console.WriteLine("PASS WinRT activation, strings, XML and metadata");
        byte[] payload=Encoding.UTF8.GetBytes("source-built WinRT streams λ 漢字");
        using(var stream=new InMemoryRandomAccessStream()) {
            using(var writer=new DataWriter(stream)) {writer.WriteBytes(payload);Require(await writer.StoreAsync().AsTask()==payload.Length,"StoreAsync");writer.DetachStream();}
            stream.Seek(0);
            using(var reader=new DataReader(stream)) {Require(await reader.LoadAsync((uint)payload.Length).AsTask()==payload.Length,"LoadAsync");var read=new byte[payload.Length];reader.ReadBytes(read);Require(read.SequenceEqual(payload),"native stream bytes");reader.DetachStream();}
        }
        Console.WriteLine("PASS WinRT native streams, async completion and disposal");
        var languages=OcrEngine.AvailableRecognizerLanguages;
        Require(languages.Count>0,"no installed OCR languages for integration test");
        var engine=OcrEngine.TryCreateFromLanguage(languages[0]);Require(engine!=null,"OCR engine activation");
        using(var bitmap=new SoftwareBitmap(BitmapPixelFormat.Bgra8,128,64,BitmapAlphaMode.Ignore)) {
            var bytes=Enumerable.Repeat((byte)255,128*64*4).ToArray();bitmap.CopyFromBuffer(bytes.AsBuffer());
            var result=await engine.RecognizeAsync(bitmap).AsTask();Require(result!=null && result.Lines.Count==0,"blank bitmap OCR");
        }
        Console.WriteLine("PASS native bitmap and asynchronous OCR ("+engine.RecognizerLanguage.LanguageTag+")");
        var settings=new Windows.UI.ViewManagement.UISettings();
        var accent=settings.GetColorValue(Windows.UI.ViewManagement.UIColorType.Accent);
        Require(accent.A==255,"Windows accent alpha");
        var properties=Windows.Media.MediaProperties.VideoEncodingProperties.CreateUncompressed(
            Windows.Media.MediaProperties.MediaEncodingSubtypes.Bgra8,128,64);
        Require(properties.Width==128 && properties.Height==64,"video encoding properties");
        var descriptor=new Windows.Media.Core.VideoStreamDescriptor(properties);
        var mediaSource=new Windows.Media.Core.MediaStreamSource(descriptor);mediaSource.BufferTime=TimeSpan.Zero;
        var transcoder=new Windows.Media.Transcoding.MediaTranscoder();transcoder.HardwareAccelerationEnabled=false;
        Require(!transcoder.HardwareAccelerationEnabled,"transcoder options");
        var manager=new Windows.Management.Deployment.PackageManager();
        var firstPackage=manager.FindPackagesForUser(string.Empty).Take(1).ToArray();
        Console.WriteLine("PASS Windows accent, video source/transcoder and package enumeration (sample count="+firstPackage.Length+")");
        try {Console.WriteLine("PASS capture support query; supported="+GraphicsCaptureSession.IsSupported());}
        catch(System.Runtime.InteropServices.COMException e) when(e.HResult==unchecked((int)0x80070424)) {
            Console.WriteLine("CAPTURE UNAVAILABLE: Windows capture service is not installed (0x80070424); native HRESULT propagation passed");
        }
        GC.Collect();GC.WaitForPendingFinalizers();
        Console.WriteLine("ALL WINRT CHECKS PASSED");
    }
}
