#include <cstdio>
#include <memory>
#include "v8/src/heap/base/stack.h"

class Visitor final : public heap::base::StackVisitor {
 public:
  explicit Visitor(const void* expected) : expected_(expected) {}
  void VisitPointer(const void* address) override {
    if (address == expected_) seen = true;
  }
  bool seen = false;
 private:
  const void* expected_;
};

int main() {
  int local = 42;
  if (!heap::base::Stack::IsOnStack(&local)) return 1;
  auto visitor = std::make_unique<Visitor>(&local);
  void* volatile root_on_stack = &local;
  heap::base::Stack stack;
  stack.SetStackStart();
  stack.IteratePointersForTesting(visitor.get());
  if (!visitor->seen || root_on_stack != &local) return 2;
  std::puts("PASS: packaged heap-base exports and Windows conservative stack scan");
}
