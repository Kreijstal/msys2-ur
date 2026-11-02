// SPDX-License-Identifier: MIT
using System;
using System.IO;
using System.Runtime.ExceptionServices;
using System.Runtime.InteropServices;
using System.Security.Cryptography.X509Certificates;
using System.Threading;
using Microsoft.Win32.SafeHandles;
namespace Microsoft.Security.Extensions
{
    public enum SignatureKind { None=0,Embedded=1,Catalog=2 }
    public enum SignatureState { Unsigned=0,SignedAndTrusted=1,SignedAndNotTrusted=2,Invalid=3 }
    public enum SignatureStateReason { Unknown=0,None=1,Revoked=2,ExplicitUserDistrust=3,CertExpired=4,UntrustedRoot=5,BadDigest=6,NoSignerCert=7,ErrCertSignature=8,ErrCertWrongUsage=9,UnspecifiedError=10 }
    public sealed class FileSignatureInfo
    {
        public bool IsOSBinary { get; }
        public SignatureKind Kind { get; }
        public SignatureState State { get; }
        public SignatureStateReason StateReason { get; }
        public X509Certificate2 SigningCertificate { get; }
        public X509Certificate2 TimestampCertificate { get; }
        private FileSignatureInfo(NativeResult data)
        {
            IsOSBinary=data.IsOSBinary!=0;Kind=(SignatureKind)data.Kind;
            State=(SignatureState)data.State;StateReason=(SignatureStateReason)data.Reason;
            X509Certificate2 signer=null,timestamp=null;
            try
            {
                signer=Certificate(data.Signer,data.SignerLength);
                timestamp=Certificate(data.Timestamp,data.TimestampLength);
                SigningCertificate=signer;TimestampCertificate=timestamp;
            }
            catch{signer?.Dispose();timestamp?.Dispose();throw;}
        }
        private static X509Certificate2 Certificate(IntPtr pointer,uint length)
        {
            if(pointer==IntPtr.Zero)return null;
            var bytes=new byte[checked((int)length)];Marshal.Copy(pointer,bytes,0,bytes.Length);
            return new X509Certificate2(bytes);
        }
        public static FileSignatureInfo GetFromFileStream(FileStream file)
        {
            ArgumentNullException.ThrowIfNull(file);
            if(!OperatingSystem.IsWindows())throw new PlatformNotSupportedException("Windows signature verification is required.");
            SafeFileHandle currentHandle=file.SafeFileHandle;
            if(currentHandle.IsClosed)throw new ObjectDisposedException(nameof(file));
            if(!file.CanRead)throw new ArgumentException("The file stream must be open and readable.",nameof(file));
            // Some installed signature providers use COM. Keep them on an STA
            // without changing the caller's apartment or exposing UI.
            lock(file)
            {
                SafeFileHandle handle=currentHandle;string name=file.Name;
                FileSignatureInfo value=null;ExceptionDispatchInfo error=null;
                void Read()
                {
                    try{value=ReadNative(handle,name);}
                    catch(Exception e){error=ExceptionDispatchInfo.Capture(e);}
                }
                if(Thread.CurrentThread.GetApartmentState()==ApartmentState.STA)Read();
                else
                {
                    var thread=new Thread(Read){IsBackground=true};thread.SetApartmentState(ApartmentState.STA);thread.Start();thread.Join();
                }
                error?.Throw();return value;
            }
        }
        private static FileSignatureInfo ReadNative(SafeFileHandle handle,string name)
        {
            if(Abi()!=1)throw new InvalidOperationException("Signature backend ABI mismatch.");
            var data=new NativeResult { Size=(uint)Marshal.SizeOf<NativeResult>() };
            try
            {
                int status=Query(handle,name,ref data);
                if(status<0)Marshal.ThrowExceptionForHR(status);
                return new FileSignatureInfo(data);
            }
            finally{Free(ref data);}
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct NativeResult
        {
            internal uint Size;internal int State,Reason,Kind,IsOSBinary;internal uint NativeError;
            internal IntPtr Signer;internal uint SignerLength;internal IntPtr Timestamp;internal uint TimestampLength;
        }
        [DllImport("msys-file-signature.dll",EntryPoint="msys_signature_abi",CallingConvention=CallingConvention.Cdecl)]private static extern uint Abi();
        [DllImport("msys-file-signature.dll",EntryPoint="msys_signature_query",CallingConvention=CallingConvention.Cdecl,CharSet=CharSet.Unicode)]private static extern int Query(SafeFileHandle handle,string path,ref NativeResult result);
        [DllImport("msys-file-signature.dll",EntryPoint="msys_signature_free",CallingConvention=CallingConvention.Cdecl)]private static extern void Free(ref NativeResult result);
    }
}
