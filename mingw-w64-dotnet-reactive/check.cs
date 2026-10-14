using System;
using System.Linq;
using System.Collections.Generic;
using System.Reactive.Linq;
using System.Reactive.Subjects;
using System.Reactive.Concurrency;
delegate void ChangedHandler(object sender,EventArgs args);
delegate void ValueHandler(int value);
class Source {public event ChangedHandler Changed;public event ValueHandler Value;public void Raise(){Changed?.Invoke(this,EventArgs.Empty);Value?.Invoke(7);}}
class Check {static void Main(){var values=new List<int>();bool completed=false;Observable.Range(1,10,ImmediateScheduler.Instance).Where(x=>x%2==0).Select(x=>x*3).Subscribe(values.Add,()=>completed=true);if(!completed||!values.SequenceEqual(new[]{6,12,18,24,30}))throw new Exception("observable operators/completion");using var subject=new Subject<int>();int total=0;var subscription=subject.Subscribe(v=>total+=v);subject.OnNext(3);subscription.Dispose();subject.OnNext(10);if(total!=3)throw new Exception("subscription disposal");var source=new Source();int changes=0,valueTotal=0;using(var changed=Observable.FromEventPattern<ChangedHandler,EventArgs>(h=>source.Changed+=h,h=>source.Changed-=h).Subscribe(e=>{if(e.Sender!=source)throw new Exception("event sender");changes++;}))using(var value=Observable.FromEvent<ValueHandler,int>(h=>source.Value+=h,h=>source.Value-=h).Subscribe(v=>valueTotal+=v)){source.Raise();}source.Raise();if(changes!=1||valueTotal!=7)throw new Exception("reflective event delegate creation/disposal");Console.WriteLine("PASS System.Reactive operators, synchronous scheduling, completion and subscription lifetime");}}
