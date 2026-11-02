"""Preserve zero-byte accept behavior across original Framework and source NET8."""
def port(text):
    original = 'asyncResult => ((Socket)asyncResult.AsyncState).EndAccept(asyncResult),'
    assert text.count(original) == 2
    position = text.index('public static Task<Socket> AcceptAsync(this Socket socket, Socket acceptSocket)')
    start = text.index(original, position)
    replacement = '''asyncResult =>
                {
                    byte[] acceptedBuffer;
                    return ((Socket)asyncResult.AsyncState).EndAccept(out acceptedBuffer, asyncResult);
                },'''
    return text[:start] + replacement + text[start + len(original):]
