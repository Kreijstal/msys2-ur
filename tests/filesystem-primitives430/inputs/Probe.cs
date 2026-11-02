using System;
using System.IO;
class Probe
{
    public static FileAccess Keep(FileAccess value) { return value; }
    static int Main()
    {
        if ((int)Keep(FileAccess.Read | FileAccess.Write) != 3 || FileMode.OpenOrCreate != (FileMode)4 || (int)(FileShare.Read | FileShare.Delete) != 5 || (FileAttributes.Hidden | FileAttributes.ReadOnly) != (FileAttributes)3) throw new Exception("Original enum flags and values");
        return 0;
    }
}
