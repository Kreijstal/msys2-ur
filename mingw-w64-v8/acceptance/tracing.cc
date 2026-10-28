// Verify V8 GC events through the packaged shared or static Perfetto runtime.
#include <cstdio>
#include <fstream>
#include <memory>
#include <string>
#include <vector>
#include "libplatform/libplatform.h"
#include "v8.h"
#include "perfetto/tracing.h"
#include "protos/perfetto/config/trace_config.gen.h"
#include "protos/perfetto/config/track_event/track_event_config.gen.h"

int main(int argc, char** argv) {
  if (argc != 2) return 10;
  if (!v8::V8::InitializeICUDefaultLocation(argv[0])) return 11;
  perfetto::TracingInitArgs args;
  args.backends = perfetto::kInProcessBackend;
  perfetto::Tracing::Initialize(args);
  auto platform = v8::platform::NewDefaultPlatform();
  v8::V8::InitializePlatform(platform.get());
  if (!v8::V8::Initialize()) return 12;
  perfetto::TraceConfig config;
  config.add_buffers()->set_size_kb(4096);
  auto* source = config.add_data_sources()->mutable_config();
  source->set_name("track_event");
  perfetto::protos::gen::TrackEventConfig events;
  events.add_enabled_categories("v8");
  events.add_enabled_categories("disabled-by-default-v8.gc");
  source->set_track_event_config_raw(events.SerializeAsString());
  auto session = perfetto::Tracing::NewTrace();
  session->Setup(config);
  session->StartBlocking();
  auto allocator = std::unique_ptr<v8::ArrayBuffer::Allocator>(v8::ArrayBuffer::Allocator::NewDefaultAllocator());
  v8::Isolate::CreateParams params;
  params.array_buffer_allocator = allocator.get();
  auto* isolate = v8::Isolate::New(params);
  {
    v8::Isolate::Scope isolate_scope(isolate);
    v8::HandleScope handles(isolate);
    auto context = v8::Context::New(isolate);
    v8::Context::Scope context_scope(context);
    auto code = v8::String::NewFromUtf8Literal(isolate, "Array.from({length:10000},(_,i)=>({i})); 42");
    auto script = v8::Script::Compile(context, code).ToLocalChecked();
    if (script->Run(context).ToLocalChecked()->Int32Value(context).FromMaybe(0) != 42) return 13;
    isolate->LowMemoryNotification();
  }
  isolate->Dispose();
  session->StopBlocking();
  auto bytes = session->ReadTraceBlocking();
  std::ofstream trace(argv[1], std::ios::binary);
  trace.write(bytes.data(), bytes.size());
  trace.close();
  std::string text(bytes.begin(), bytes.end());
  bool found = text.find("V8.GC") != std::string::npos;
  session.reset();
  v8::V8::Dispose();
  v8::V8::DisposePlatform();
  platform.reset();
  perfetto::Tracing::Shutdown();
  if (!found) { std::fputs("FAIL: no V8 GC event in shared Perfetto trace\n", stderr); return 14; }
  std::printf("PASS: packaged Perfetto observed V8 GC events (%zu trace bytes)\n", bytes.size());
}
