using System;
using System.Linq;
using System.Text;
using Org.BouncyCastle.Crypto;
using Org.BouncyCastle.Crypto.Digests;
using Org.BouncyCastle.Crypto.Engines;
using Org.BouncyCastle.Crypto.Generators;
using Org.BouncyCastle.Crypto.Modes;
using Org.BouncyCastle.Crypto.Parameters;
using Org.BouncyCastle.Crypto.Signers;
using Org.BouncyCastle.Security;
using Org.BouncyCastle.Utilities.Encoders;
class Check {
static byte[] Sha256(byte[] data){var d=new Sha256Digest();d.BlockUpdate(data,0,data.Length);var o=new byte[d.GetDigestSize()];d.DoFinal(o,0);return o;}
static byte[] Gcm(bool enc,byte[] key,byte[] iv,byte[] aad,byte[] input){var c=new GcmBlockCipher(new AesEngine());c.Init(enc,new AeadParameters(new KeyParameter(key),128,iv,aad));var o=new byte[c.GetOutputSize(input.Length)];int n=c.ProcessBytes(input,0,input.Length,o,0);n+=c.DoFinal(o,n);return o.Take(n).ToArray();}
static void Main(){
var asm=typeof(Sha256Digest).Assembly.GetName();
if(asm.Name!="BouncyCastle.Cryptography"||Hex.ToHexString(asm.GetPublicKeyToken())!="072edcf4a5328938")throw new Exception("strong-name identity "+asm.FullName);
if(Hex.ToHexString(Sha256(Encoding.ASCII.GetBytes("abc")))!="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")throw new Exception("SHA-256 FIPS 180-2 abc vector");
// NIST GCM test case 4 (AES-128, 60-byte plaintext, 20-byte AAD)
var key=Hex.Decode("feffe9928665731c6d6a8f9467308308");var iv=Hex.Decode("cafebabefacedbaddecaf888");var aad=Hex.Decode("feedfacedeadbeeffeedfacedeadbeefabaddad2");
var pt=Hex.Decode("d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a721c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b39");
var ct=Gcm(true,key,iv,aad,pt);
if(Hex.ToHexString(ct)!="42831ec2217774244b7221b784d0d49ce3aa212f2c02a4e035c17e2329aca12e21d514b25466931c7d8f6a5aac84aa051ba30b396a0aac973d58e0915bc94fbc3221a5db94fae95ae7121a47")throw new Exception("AES-GCM NIST test case 4");
if(!Gcm(false,key,iv,aad,ct).SequenceEqual(pt))throw new Exception("AES-GCM decrypt round trip");
ct[3]^=1;try{Gcm(false,key,iv,aad,ct);throw new Exception("AES-GCM accepted tampered ciphertext");}catch(InvalidCipherTextException){}
// RFC 8032 Ed25519 test 1 (empty message) plus a generated key pair
var sk=new Ed25519PrivateKeyParameters(Hex.Decode("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"),0);
if(Hex.ToHexString(sk.GeneratePublicKey().GetEncoded())!="d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")throw new Exception("Ed25519 RFC 8032 public key");
var s=new Ed25519Signer();s.Init(true,sk);var sig=s.GenerateSignature();
if(Hex.ToHexString(sig)!="e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")throw new Exception("Ed25519 RFC 8032 signature");
var gen=new Ed25519KeyPairGenerator();gen.Init(new Ed25519KeyGenerationParameters(new SecureRandom()));var kp=gen.GenerateKeyPair();
var msg=Encoding.UTF8.GetBytes("Bouncy Castle λ 🐾");s=new Ed25519Signer();s.Init(true,kp.Private);s.BlockUpdate(msg,0,msg.Length);sig=s.GenerateSignature();
var v=new Ed25519Signer();v.Init(false,kp.Public);v.BlockUpdate(msg,0,msg.Length);if(!v.VerifySignature(sig))throw new Exception("Ed25519 verify");
msg[0]^=1;v=new Ed25519Signer();v.Init(false,kp.Public);v.BlockUpdate(msg,0,msg.Length);if(v.VerifySignature(sig))throw new Exception("Ed25519 accepted tampered message");
Console.WriteLine("PASS BouncyCastle.Cryptography "+asm.Version+" strong-named "+asm.FullName.Split(", ").Last()+"; SHA-256 abc, AES-128-GCM NIST vector/round trip/tamper rejection, Ed25519 RFC 8032 vector and generated-key sign/verify/tamper rejection");}}
