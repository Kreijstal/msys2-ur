using Microsoft.Extensions.Logging;
public static partial class Invalid
{
    [LoggerMessage(EventId=1,Message="Missing log level")]
    public static partial void MissingLevel(ILogger logger);
}
