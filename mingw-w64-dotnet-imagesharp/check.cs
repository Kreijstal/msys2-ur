using System;
using System.IO;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;
using SixLabors.ImageSharp.Formats;
using SixLabors.ImageSharp.Formats.Png;
using SixLabors.ImageSharp.Formats.Tiff;
using SixLabors.ImageSharp.Formats.Bmp;
using SixLabors.ImageSharp.Formats.Jpeg;
using SixLabors.ImageSharp.Formats.Gif;
using SixLabors.ImageSharp.Processing;
class Check {static void Main(){using var image=new Image<Rgba32>(32,24);for(int y=0;y<24;y++)for(int x=0;x<32;x++)image[x,y]=new Rgba32((byte)(x*7),(byte)(y*9),123,(byte)(100+x*4));foreach(IImageEncoder encoder in new IImageEncoder[]{new PngEncoder(),new TiffEncoder(){BitsPerPixel=TiffBitsPerPixel.Bit24}}){using var data=new MemoryStream();image.Save(data,encoder);data.Position=0;using var decoded=Image.Load<Rgba32>(data);if(decoded.Width!=32||decoded.Height!=24)throw new Exception("dimensions");for(int y=0;y<24;y++)for(int x=0;x<32;x++)if(!decoded[x,y].Equals(encoder is TiffEncoder?new Rgba32(image[x,y].R,image[x,y].G,image[x,y].B,255):image[x,y]))throw new Exception($"lossless pixel round trip: {encoder.GetType()} at {x},{y}: source={image[x,y]}, decoded={decoded[x,y]}");}using var opaque=new Image<Rgba32>(32,24,new Rgba32(220,40,60));foreach(IImageEncoder encoder in new IImageEncoder[]{new BmpEncoder(),new GifEncoder(),new JpegEncoder(){Quality=95}}){using var data=new MemoryStream();opaque.Save(data,encoder);data.Position=0;using var decoded=Image.Load<Rgba32>(data);var pixel=decoded[16,12];if(decoded.Width!=32||decoded.Height!=24||Math.Abs(pixel.R-220)>4||Math.Abs(pixel.G-40)>4||Math.Abs(pixel.B-60)>4)throw new Exception("codec pixels: "+encoder.GetType());}image.Mutate(c=>c.Resize(16,12).Rotate(RotateMode.Rotate90));if(image.Width!=12||image.Height!=16)throw new Exception("processing geometry");Console.WriteLine("PASS ImageSharp PNG exact RGBA/TIFF exact RGB24, BMP/GIF/JPEG real codec pixels and resize/rotation");}}
