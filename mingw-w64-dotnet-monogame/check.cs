using System;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Audio;
using Microsoft.Xna.Framework.Content;
using Microsoft.Xna.Framework.Graphics;

class Check
{
    static void Fail(string message) { Console.Error.WriteLine("FAIL: " + message); Environment.Exit(1); }

    static void Main(string[] args)
    {
        // 1. The stock effects in MonoGame.Framework.dll are the ones compiled
        //    from source by this package's mgfxc (MGFX container, OpenGL/MojoShader GLSL).
        var asm = typeof(Game).Assembly;
        var effects = asm.GetManifestResourceNames().Where(n => n.EndsWith(".ogl.mgfxo")).OrderBy(n => n).ToArray();
        if (effects.Length != 6) Fail("expected 6 stock effects, found " + string.Join(",", effects));
        foreach (var name in effects)
        {
            using var s = asm.GetManifestResourceStream(name)!;
            var head = new byte[4];
            s.ReadExactly(head);
            if (System.Text.Encoding.ASCII.GetString(head) != "MGFX" || s.Length < 256) Fail(name + " is not a compiled effect");
            Console.WriteLine($"{name}: {s.Length} bytes");
        }

        // 2. SDL2 and OpenAL Soft were copied next to the app from the MSYS2 prefix.
        var dir = AppContext.BaseDirectory;
        foreach (var dll in new[] { "SDL2.dll", "libopenal-1.dll" })
        {
            if (!File.Exists(Path.Combine(dir, dll))) Fail(dll + " was not copied to the output directory");
            NativeLibrary.Free(NativeLibrary.Load(Path.Combine(dir, dll)));
        }

        // 3. OpenAL through MonoGame's own binding (no audio device is fine on a build host).
        try
        {
            using var sound = new SoundEffect(new byte[22050 * 2], 22050, AudioChannels.Mono);
            Console.WriteLine($"SoundEffect: {sound.Duration.TotalSeconds:0.00}s");
        }
        catch (NoAudioHardwareException e) { Console.WriteLine("no audio hardware: " + e.Message); }

        // 4. Content built by mgcb: XNB headers for the DesktopGL target, and a
        //    device-independent asset through the ContentManager.
        var content = args[0];
        foreach (var file in Directory.GetFiles(content, "*.xnb"))
        {
            var b = File.ReadAllBytes(file);
            if (b.Length < 10 || b[0] != 'X' || b[1] != 'N' || b[2] != 'B' || b[3] != 'd') Fail(file + " is not a DesktopGL XNB");
            Console.WriteLine($"{Path.GetFileName(file)}: {b.Length} bytes");
        }
        var manager = new ContentManager(new GameServiceContainer(), content);
        var data = manager.Load<string[]>("data");
        if (string.Join(",", data) != "MonoGame,MSYS2") Fail("data.xnb round trip: " + string.Join(",", data));
        Console.WriteLine("MonoGame check OK");
    }
}
