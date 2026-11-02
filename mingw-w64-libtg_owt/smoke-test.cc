// Links against the freshly built libtg_owt through its exported CMake
// package and exercises the Windows-specific code the MinGW patches touch:
// the Windows.Graphics.Capture capturer (with the hand-written Closed-event
// delegate), the GDI/DXGI fallbacks and the libyuv-backed video buffers.
#include <cstdio>
#include <memory>

#include "api/video/i420_buffer.h"
#include "modules/desktop_capture/desktop_capture_options.h"
#include "modules/desktop_capture/desktop_capturer.h"
#include "modules/desktop_capture/win/wgc_capturer_win.h"

int main() {
  auto buffer = webrtc::I420Buffer::Create(64, 48);
  webrtc::I420Buffer::SetBlack(buffer.get());
  auto scaled = buffer->Scale(32, 24);
  if (!scaled || scaled->width() != 32 || scaled->height() != 24) {
    std::fprintf(stderr, "I420 scaling failed\n");
    return 1;
  }

  auto options = webrtc::DesktopCaptureOptions::CreateDefault();
  options.set_allow_wgc_screen_capturer(true);
  options.set_allow_wgc_window_capturer(true);
  std::printf("WGC supported: screen=%d window=%d\n",
              webrtc::IsWgcSupported(webrtc::CaptureType::kScreen),
              webrtc::IsWgcSupported(webrtc::CaptureType::kWindow));

  // Whatever backend gets picked, creating it and listing sources must work
  // even in a non-interactive session (it may simply find nothing).
  auto screen = webrtc::DesktopCapturer::CreateScreenCapturer(options);
  auto window = webrtc::DesktopCapturer::CreateWindowCapturer(options);
  if (!screen || !window) {
    std::fprintf(stderr, "failed to create desktop capturers\n");
    return 1;
  }
  webrtc::DesktopCapturer::SourceList screens, windows;
  screen->GetSourceList(&screens);
  window->GetSourceList(&windows);
  std::printf("screens=%zu windows=%zu\n", screens.size(), windows.size());
  return 0;
}
