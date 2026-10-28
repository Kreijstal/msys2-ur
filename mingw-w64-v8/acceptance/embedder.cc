#include <cstdio>
#include <cstdlib>
#include <memory>
#include "v8.h"
#include "libplatform/libplatform.h"

static void Check(bool value, const char* reason) {
  if (!value) { std::fprintf(stderr, "FAIL: %s\n", reason); std::exit(1); }
}

static v8::Local<v8::Value> Eval(v8::Isolate* isolate, v8::Local<v8::Context> context,
                                const char* text) {
  v8::Local<v8::String> source;
  Check(v8::String::NewFromUtf8(isolate, text).ToLocal(&source), "source string");
  v8::Local<v8::Script> script;
  Check(v8::Script::Compile(context, source).ToLocal(&script), "compile JavaScript");
  v8::Local<v8::Value> result;
  Check(script->Run(context).ToLocal(&result), "execute JavaScript");
  return result;
}

int main(int argc, char** argv) {
  Check(v8::V8::InitializeICUDefaultLocation(argv[0]), "initialize system ICU");
  auto platform = v8::platform::NewDefaultPlatform();
  v8::V8::InitializePlatform(platform.get());
  Check(v8::V8::Initialize(), "initialize V8");
  auto allocator = std::unique_ptr<v8::ArrayBuffer::Allocator>(
      v8::ArrayBuffer::Allocator::NewDefaultAllocator());
  v8::Isolate::CreateParams params;
  params.array_buffer_allocator = allocator.get();
  auto* isolate = v8::Isolate::New(params);
  {
    v8::Isolate::Scope scope(isolate);
    v8::HandleScope handles(isolate);
    auto context = v8::Context::New(isolate);
    v8::Context::Scope entered(context);
    const char* program = R"JS(
      (() => {
        const check = (x) => { if (!x) throw new Error('engine regression'); };
        check(21n * 2n === 42n);
        check(new Intl.NumberFormat('de-DE').format(1234.5) === '1.234,5');
        check('i'.toLocaleUpperCase('tr') === '\u0130');
        const module = new WebAssembly.Module(new Uint8Array([
          0,97,115,109,1,0,0,0,1,5,1,96,0,1,127,3,2,1,0,
          7,10,1,6,97,110,115,119,101,114,0,0,10,6,1,4,0,65,42,11]));
        check(new WebAssembly.Instance(module).exports.answer() === 42);
        globalThis.asyncAnswer = 0;
        Promise.resolve(21).then(x => { globalThis.asyncAnswer = x * 2; });
        return 42;
      })()
    )JS";
    Check(Eval(isolate, context, program)->Int32Value(context).FromMaybe(0) == 42, "JS/Wasm/ICU");
    isolate->PerformMicrotaskCheckpoint();
    Check(Eval(isolate, context, "asyncAnswer")->Int32Value(context).FromMaybe(0) == 42, "async microtasks");
    isolate->LowMemoryNotification();
  }
  isolate->Dispose();

  v8::StartupData blob;
  {
    v8::SnapshotCreator creator;
    auto* snapshot_isolate = creator.GetIsolate();
    {
      v8::HandleScope handles(snapshot_isolate);
      auto context = v8::Context::New(snapshot_isolate);
      v8::Context::Scope entered(context);
      Eval(snapshot_isolate, context, "globalThis.savedAnswer = 42");
      creator.SetDefaultContext(context);
    }
    blob = creator.CreateBlob(v8::SnapshotCreator::FunctionCodeHandling::kKeep);
  }
  Check(blob.data && blob.raw_size > 0, "create consumer snapshot");
  params.snapshot_blob = &blob;
  isolate = v8::Isolate::New(params);
  {
    v8::Isolate::Scope scope(isolate);
    v8::HandleScope handles(isolate);
    auto context = v8::Context::New(isolate);
    v8::Context::Scope entered(context);
    Check(Eval(isolate, context, "savedAnswer")->Int32Value(context).FromMaybe(0) == 42, "restore consumer snapshot");
  }
  isolate->Dispose();
  delete[] blob.data;
  v8::V8::Dispose();
  v8::V8::DisposePlatform();
  std::puts("PASS: JS, async, Wasm, ICU, GC, consumer snapshot");
}
