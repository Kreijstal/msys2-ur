using System;
using System.IO;
using SixLabors.Fonts;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;
using SixLabors.ImageSharp.Processing;
using SixLabors.ImageSharp.Drawing;
using SixLabors.ImageSharp.Drawing.Processing;
class Check {static void Main(){using var image=new Image<Rgba32>(96,64);var font=new FontCollection().Add("C:/Windows/Fonts/segoeui.ttf").CreateFont(18);image.Mutate(c=>c.Fill(Color.Red,new RectangularPolygon(2,2,20,20)).Draw(Color.Blue,2,new EllipsePolygon(50,16,10)).DrawText("λ",font,Color.Lime,new PointF(4,34)));if(!image[10,10].Equals(new Rgba32(255,0,0))||image[95,63].A!=0)throw new Exception("filled geometry and transparent outside");int blue=0,green=0;for(int y=0;y<64;y++)for(int x=0;x<96;x++){var pixel=image[x,y];if(pixel.B>180&&pixel.R<40&&pixel.G<40)blue++;if(pixel.G>180&&pixel.R<40&&pixel.B<40)green++;}if(blue<20||green<5)throw new Exception("actual stroked path and font glyph raster");using var stream=new MemoryStream();image.SaveAsPng(stream);stream.Position=0;using var copy=Image.Load<Rgba32>(stream);for(int y=0;y<64;y++)for(int x=0;x<96;x++)if(!image[x,y].Equals(copy[x,y]))throw new Exception("drawing PNG round trip");Console.WriteLine("PASS ImageSharp.Drawing real filled/stroked geometry, Greek glyph raster and exact PNG output");}}
