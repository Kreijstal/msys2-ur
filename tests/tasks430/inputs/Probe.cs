using System.Threading.Tasks;
public static class Probe
{
    public static Task<int> Create(int value)
    {
        var completion = new TaskCompletionSource<int>();
        completion.SetResult(value);
        return completion.Task;
    }
    public static Task Combine(Task[] tasks) { return Task.WhenAll(tasks); }
#if TASKS13
    public static Task Completed() { return Task.CompletedTask; }
    public static TaskCreationOptions Continuations() { return TaskCreationOptions.RunContinuationsAsynchronously; }
#endif
}
