"""Exercise the packaged stdio server and a kernel shared with a manual client."""

import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from jupyter_client import KernelManager
import ipython_kernel_mcp.server as bridge


def main():
    kernel = KernelManager()
    client = None
    server = None
    try:
        # Avoid a user kernelspec pointing at another Python installation.
        kernel.kernel_spec.argv = [
            sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"
        ]
        kernel.start_kernel()
        client = kernel.blocking_client()
        client.start_channels()
        client.wait_for_ready(timeout=30)
        reply = client.execute_interactive("data = [3, 5, 7]", timeout=20)
        assert reply["content"]["status"] == "ok", reply

        server = subprocess.Popen(
            [sys.executable, "-m", "ipython_kernel_mcp.server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=dict(os.environ, IPYTHON_MCP_CONNECTION=kernel.connection_file),
        )
        replies = queue.Queue()

        def read_replies():
            for line in server.stdout:
                try:
                    replies.put(json.loads(line))
                except json.JSONDecodeError:
                    replies.put({"invalid_stdout": line})
            replies.put({"eof": True})

        threading.Thread(target=read_replies, daemon=True).start()
        next_id = 0

        def rpc(method, params=None, notification=False):
            nonlocal next_id
            next_id += 1
            request = {"jsonrpc": "2.0", "method": method}
            if not notification:
                request["id"] = next_id
            if params is not None:
                request["params"] = params
            server.stdin.write(json.dumps(request) + "\n")
            server.stdin.flush()
            if notification:
                return None
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                response = replies.get(timeout=max(0.1, deadline - time.monotonic()))
                if response.get("eof"):
                    raise RuntimeError("MCP exited: " + server.stderr.read())
                assert "invalid_stdout" not in response, response
                if response.get("id") == request["id"]:
                    assert "error" not in response, response
                    return response["result"]
            raise TimeoutError(method)

        def call(name, arguments=None):
            result = rpc("tools/call", {"name": name, "arguments": arguments or {}})
            assert not result.get("isError"), result
            return "\n".join(
                part["text"] for part in result["content"] if part["type"] == "text"
            )

        # Match the protocol version and framing used by llama-server.
        rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "msys2ur-package-check", "version": "1"},
        })
        rpc("notifications/initialized", {}, notification=True)
        names = {tool["name"] for tool in rpc("tools/list", {})["tools"]}
        assert names == {
            "connect_to_kernel", "execute_code", "kernel_status", "interrupt_kernel"
        }, names
        assert "Connected to IPython kernel" in call("connect_to_kernel")
        assert call("execute_code", {"code": "print(data)"}).strip() == "[3, 5, 7]"
        call("execute_code", {"code": "intermediate = sum(data)"})
        assert call("execute_code", {"code": "print(intermediate)"}).strip() == "15"

        # Code entered manually sees the tool's variable and updates shared data.
        reply = client.execute_interactive("assert intermediate == 15; data.append(11)", timeout=20)
        assert reply["content"]["status"] == "ok", reply
        assert call("execute_code", {"code": "print(sum(data))"}).strip() == "26"

        # Windows IPython rejects interrupt_request. Report that honestly and
        # leave interruption to the user's kernel console, not another process.
        if sys.platform == "win32":
            assert "not supported on Windows" in call("interrupt_kernel")
            print("PASS: 4 tools; llama-compatible stdio; shared data; persistent state; Windows interrupt notice")
            print("Checked module:", Path(bridge.__file__).resolve())
            return

        # On POSIX, manual execution can be interrupted through the control channel.
        execution_id = client.execute("import time; time.sleep(60)")
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            message = client.get_iopub_msg(timeout=20)
            if (message["parent_header"].get("msg_id") == execution_id
                    and message["msg_type"] == "status"
                    and message["content"]["execution_state"] == "busy"):
                break
        else:
            raise TimeoutError("manual execution did not start")
        assert "Sent interrupt request" in call("interrupt_kernel")
        reply = client.get_shell_msg(timeout=20)
        assert reply["parent_header"]["msg_id"] == execution_id, reply
        assert reply["content"].get("ename") == "KeyboardInterrupt", reply
        assert call("execute_code", {"code": "print(intermediate)"}).strip() == "15"
        print("PASS: 4 tools; llama-compatible stdio; shared data; persistent state; targeted interrupt")
        print("Checked module:", Path(bridge.__file__).resolve())
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        if client is not None:
            client.stop_channels()
        if kernel.has_kernel:
            kernel.shutdown_kernel(now=True)


if __name__ == "__main__":
    main()
