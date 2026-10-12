# IPython kernel MCP for UCRT64

This package connects llama-server to an existing IPython kernel. A terminal,
notebook, or IDE connected to that same kernel can load data and execute code
manually. Variables and intermediate results survive MCP tool calls.

The package pins upstream commit `3c0c701066342668dc9f56a25609f1167c030b8a`.
Its interrupt tool is patched to address the connected kernel through Jupyter's
control channel on POSIX, instead of signalling whichever ipykernel process
happens to be found first. Windows IPython rejects protocol interruption;
the tool reports that limitation and leaves interruption to the kernel console.

## Build and install

Run these commands from the repository root in an **MSYS2 UCRT64 shell**.
The HTTP client and versioning recipes already live in this repository; the
MCP SDK, wire types, and kernel bridge are added alongside them.

```bash
for package in \
  mingw-w64-python-uv-dynamic-versioning \
  mingw-w64-python-httpcore2 \
  mingw-w64-python-httpx2 \
  mingw-w64-python-mcp-types \
  mingw-w64-python-mcp \
  mingw-w64-python-ipython-kernel-mcp
do
  (
    cd "$package" || exit
    MINGW_ARCH=ucrt64 makepkg-mingw -sfi
  ) || break
done
```

Dependencies are managed by pacman. No pip installation or activated virtual
environment is needed. The MCP SDK's pywin32 dependency accepts MSYS2's build
310, which is patched and compiled for its Python 3.14. The SDK package checks
the actual standard-handle and Job Object APIs used by its Windows transport.

The bridge package's `check()` verifies tool discovery using llama-server's
MCP protocol version, manually loaded data, variables shared in both directions,
state persisting across calls, and interruption of the connected kernel on
POSIX or the explicit interruption limitation on Windows.

## Use with llama-server

Start or keep your own kernel running, and connect a console to it:

```bash
ipython kernel
# In another terminal, use the connection filename printed by the kernel:
jupyter console --existing kernel-21880.json
```

The kernel and console commands require the official UCRT64 packages
`mingw-w64-ucrt-x86_64-python-ipykernel` and
`mingw-w64-ucrt-x86_64-python-jupyter_console`. The former is installed when
building with checks enabled; the latter is an optional dependency.

Find the full connection-file path:

```bash
python -c "from pathlib import Path; from jupyter_core.paths import jupyter_runtime_dir; print((Path(jupyter_runtime_dir()) / 'kernel-21880.json').as_posix())"
```

Use the printed path in `mcp.json`. `command` must be the native Windows path
to UCRT64 Python, not an MSYS shell alias. Print it with
`python -c "import sys; from pathlib import Path; print(Path(sys.executable).as_posix())"`.

```json
{
  "mcpServers": {
    "ipython": {
      "command": "C:/Users/jpardo/msys64/ucrt64/bin/python.exe",
      "args": ["-m", "ipython_kernel_mcp.server"],
      "env": {
        "IPYTHON_MCP_CONNECTION": "C:/YOUR/ACTUAL/PATH/kernel-21880.json"
      }
    }
  }
}
```

Append `--mcp-servers-config mcp.json` to your existing llama-server command.
Startup should report `MCP warmup: 'ipython' discovered 4 tools`.
Enable the `ipython_*` server tools in the WebUI and ask the model to call
`ipython_connect_to_kernel` with no arguments. Subsequent calls to
`ipython_execute_code` use the same kernel as your console.

The bridge does not start another kernel. Tell the model which variables are
already loaded, for example: "The shared kernel already contains `data`.
Use it directly; do not reload or reconstruct it."
