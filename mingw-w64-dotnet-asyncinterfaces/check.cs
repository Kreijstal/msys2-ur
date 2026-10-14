using System;
using System.Linq;
using System.Collections.Generic;
using System.Reflection;
using System.Threading.Tasks;
class Lease:IAsyncDisposable {public bool Disposed;public ValueTask DisposeAsync(){Disposed=true;return ValueTask.CompletedTask;}}
class Check {static async IAsyncEnumerable<int> Values(){await Task.Yield();yield return 42;}static async Task Main(){var facade=Assembly.Load("Microsoft.Bcl.AsyncInterfaces");var forwarded=facade.GetForwardedTypes();if(forwarded.Length<10||!forwarded.Contains(typeof(IAsyncDisposable))||!forwarded.Contains(typeof(IAsyncEnumerable<>)))throw new Exception("original type-forwarding closure");int total=0;await foreach(var n in Values())total+=n;var lease=new Lease();await using(lease){if(total!=42)throw new Exception("async enumeration");}if(!lease.Disposed||facade.GetName().Version!=new Version(10,0,0,0)||Convert.ToHexString(facade.GetName().GetPublicKeyToken()).ToLowerInvariant()!="cc7b13ffcd2ddd51")throw new Exception("async disposal or original identity");Console.WriteLine("PASS original async-interface facade type forwards, real async enumeration/disposal and strong identity");}}
