#include <cstdio>
#include <memory>
#include "cppgc/allocation.h"
#include "cppgc/default-platform.h"
#include "cppgc/garbage-collected.h"
#include "cppgc/heap.h"
#include "cppgc/member.h"
#include "cppgc/platform.h"
#include "cppgc/persistent.h"
#include "cppgc/visitor.h"

struct Object final : cppgc::GarbageCollected<Object> {
  static inline int finalized = 0;
  explicit Object(int value) : value(value) {}
  ~Object() { ++finalized; }
  void Trace(cppgc::Visitor* visitor) const { visitor->Trace(child); }
  int value;
  cppgc::Member<Object> child;
};

int main() {
  auto platform = std::make_shared<cppgc::DefaultPlatform>();
  cppgc::InitializeProcess(platform->GetPageAllocator());
  {
    auto heap = cppgc::Heap::Create(platform);
    cppgc::Persistent<Object> root = cppgc::MakeGarbageCollected<Object>(heap->GetAllocationHandle(), 42);
    root->child = cppgc::MakeGarbageCollected<Object>(heap->GetAllocationHandle(), 21);
    heap->ForceGarbageCollectionSlow("SDK test", "root retained", cppgc::EmbedderStackState::kMayContainHeapPointers);
    // Ignore conservative stack roots so retaining the child proves Trace()
    // followed its compressed Member edge across the DLL boundary.
    heap->ForceGarbageCollectionSlow("SDK test", "trace member", cppgc::EmbedderStackState::kNoHeapPointers);
    if (Object::finalized != 0) return 1;
    if (root->value != 42 || !root->child || root->child->value != 21) return 2;
    root->child = nullptr;
    heap->ForceGarbageCollectionSlow("SDK test", "child released", cppgc::EmbedderStackState::kNoHeapPointers);
    if (Object::finalized != 1) return 3;
    root.Clear();
    heap->ForceGarbageCollectionSlow("SDK test", "root released", cppgc::EmbedderStackState::kNoHeapPointers);
    if (Object::finalized != 2) return 4;
  }
  cppgc::ShutdownProcess();
  std::puts("PASS: cppgc allocation, tracing, finalization from packaged V8");
}
