using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Dynamic;
using System.Linq;
using System.Linq.Expressions;
using System.Runtime.Serialization;
using System.Threading;
using System.Threading.Tasks;

internal static class ProbeDataflow
{
    static int Main()
    {
        Debug.Assert(false, "This conditional call must be omitted from Release IL.");
        var queue = new ConcurrentQueue<int>();
        queue.Enqueue(20);
        queue.Enqueue(22);
        if (queue.ToArray().Sum() != 42) throw new Exception("Concurrent collection/LINQ contracts");
        IDictionary<string, object> expando = new ExpandoObject();
        int notifications = 0;
        ((INotifyPropertyChanged)expando).PropertyChanged += (sender, args) => notifications++;
        expando["Answer"] = 42;
        if ((int)expando["Answer"] != 42 || notifications != 1) throw new Exception("Dynamic/ObjectModel contracts");
        var parameter = Expression.Parameter(typeof(int), "value");
        var expression = Expression.Lambda<Func<int, int>>(Expression.Add(parameter, Expression.Constant(2)), parameter);
        if (expression.Compile()(40) != 42) throw new Exception("Expression contracts");
        if (new OnDeserializedAttribute().GetType().Name != "OnDeserializedAttribute") throw new Exception("Serialization attribute contract");
        using (var gate = new SemaphoreSlim(0))
        {
            var task = Task.Run(() => gate.Release());
            if (!gate.Wait(10000)) throw new Exception("Threading/Tasks contracts");
            task.GetAwaiter().GetResult();
        }
        return 0;
    }
}
