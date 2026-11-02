#!/usr/bin/env python3
"""Check V8 GC tracing and loaded DLL identity through real content_shell CDP."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request

import websocket


class CDP:
    def __init__(self, url):
        self.socket = websocket.create_connection(url, timeout=120, suppress_origin=True)
        self.sequence = 0
        self.events = []

    def receive(self):
        message = json.loads(self.socket.recv())
        if "method" in message:
            self.events.append(message)
        return message

    def call(self, method, params=None):
        self.sequence += 1
        request = self.sequence
        self.socket.send(json.dumps({"id": request, "method": method, "params": params or {}}))
        while True:
            message = self.receive()
            if message.get("id") == request:
                if "error" in message:
                    raise ValueError(f"{method}: {message['error']}")
                return message.get("result", {})

    def wait(self, method):
        while True:
            for event in self.events:
                if event["method"] == method:
                    return event.get("params", {})
            self.receive()

    def close(self):
        self.socket.close()


def loaded_modules(pid):
    class Module(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("GlblcntUsage", wintypes.DWORD),
                    ("ProccntUsage", wintypes.DWORD), ("modBaseAddr", ctypes.c_void_p),
                    ("modBaseSize", wintypes.DWORD), ("hModule", wintypes.HMODULE),
                    ("szModule", wintypes.WCHAR * 256), ("szExePath", wintypes.WCHAR * 260)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    for function in (kernel.Module32FirstW, kernel.Module32NextW):
        function.argtypes = [wintypes.HANDLE, ctypes.POINTER(Module)]
        function.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(0x8 | 0x10, int(pid))
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    modules = {}
    try:
        entry = Module()
        entry.dwSize = ctypes.sizeof(entry)
        success = kernel.Module32FirstW(snapshot, ctypes.byref(entry))
        if not success:
            raise ctypes.WinError(ctypes.get_last_error())
        while success:
            modules[entry.szModule.lower()] = entry.szExePath
            success = kernel.Module32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    return modules


def get_json(port, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as response:
        return json.load(response)


def exercise(executable, name, evidence, manifest):
    with tempfile.TemporaryDirectory(prefix="v8-cdp-") as profile:
        log_path = evidence / (name + "-cdp.log")
        with log_path.open("w") as log:
            command = [str(executable), "--no-sandbox", "--disable-gpu", "--remote-debugging-port=0",
                       "--remote-allow-origins=*", "--user-data-dir=" + profile, "about:blank"]
            process = subprocess.Popen(command, cwd=executable.parent, stdout=log, stderr=subprocess.STDOUT)
            browser = page = None
            try:
                active_port = Path(profile) / "DevToolsActivePort"
                deadline = time.monotonic() + 120
                while not active_port.exists():
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise ValueError(f"{name}: no debugging endpoint; see {log_path}")
                    time.sleep(0.1)
                port = int(active_port.read_text().splitlines()[0])
                browser = CDP(get_json(port, "/json/version")["webSocketDebuggerUrl"])
                targets = get_json(port, "/json/list")
                target = next(target for target in targets if target["type"] == "page")
                page = CDP(target["webSocketDebuggerUrl"])
                page.call("Runtime.enable")
                browser.call("Tracing.start", {"categories": "v8,disabled-by-default-v8.gc,devtools.timeline",
                                                "transferMode": "ReportEvents"})
                for iteration in range(3):
                    result = page.call("Runtime.evaluate", {
                        "expression": "globalThis.keep = Array.from({length:100000}, (_,i)=>({i, data:'x'.repeat(128)})); globalThis.keep=null; 42",
                        "returnByValue": True})
                    if result.get("exceptionDetails") or result["result"].get("value") != 42:
                        raise ValueError(f"{name}: JS stress failed: {result}")
                    page.call("HeapProfiler.collectGarbage")
                processes = browser.call("SystemInfo.getProcessInfo")["processInfo"]
                renderer_modules = {str(item["id"]): loaded_modules(item["id"])
                                    for item in processes if item["type"] == "renderer"}
                if not renderer_modules:
                    raise ValueError(f"{name}: no renderer process")
                if manifest:
                    wanted = manifest["sha256"]["bin/libv8.dll"]
                    for pid, modules in renderer_modules.items():
                        dll = modules.get("libv8.dll")
                        if not dll or Path(dll.replace("\\", "/")).resolve().as_posix().casefold() != (executable.parent / "libv8.dll").resolve().as_posix().casefold():
                            raise ValueError(f"{name}: renderer {pid} loaded the wrong V8 DLL: {dll}")
                        with Path(dll.replace("\\", "/")).open("rb") as stream:
                            if hashlib.file_digest(stream, "sha256").hexdigest() != wanted:
                                raise ValueError("loaded V8 DLL differs from package manifest")
                else:
                    if any("libv8.dll" in modules for modules in renderer_modules.values()):
                        raise ValueError("bundled control unexpectedly loaded an external V8 DLL")
                browser.call("Tracing.end")
                completion = browser.wait("Tracing.tracingComplete")
                if completion.get("dataLossOccurred"):
                    raise ValueError(f"{name}: trace buffer lost data")
                events = [entry for event in browser.events if event["method"] == "Tracing.dataCollected"
                          for entry in event["params"]["value"]]
                gc_events = [entry for entry in events if "gc" in entry.get("name", "").lower()
                             and "v8" in entry.get("cat", "").lower()]
                if not gc_events:
                    raise ValueError(f"{name}: V8 GC events did not join Chromium's tracing session")
                (evidence / (name + "-trace.json")).write_text(json.dumps(events))
                result = {"command": command, "gc_event_count": len(gc_events),
                          "gc_event_names": sorted({entry["name"] for entry in gc_events}),
                          "renderer_modules": renderer_modules}
                if manifest:
                    result["loaded_v8_sha256"] = wanted
                print(f"{name}: {len(gc_events)} V8 GC trace events", flush=True)
                return result
            finally:
                if page:
                    page.close()
                if browser:
                    browser.close()
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundled", type=Path, required=True)
    parser.add_argument("--system", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "tracing-and-loaded-dlls.json").unlink(missing_ok=True)
    manifest = json.loads(args.manifest.read_text())
    results = {"bundled": exercise(args.bundled.resolve(), "bundled", evidence, None),
               "system": exercise(args.system.resolve(), "system", evidence, manifest)}
    (evidence / "tracing-and-loaded-dlls.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
