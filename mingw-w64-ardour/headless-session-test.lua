-- Headless smoke test for ardour-lua (luasession):
--   create a session with the "None (Dummy)" backend, add an audio track
--   carrying the bundled "ACE Noise" Lua DSP, save it, and export the
--   session range of the master bus to a WAV file.
--
-- Usage: ardour9-lua headless-session-test.lua <session-dir> <export-dir>

local sdir = arg[1]
local edir = arg[2]
assert (sdir and edir, "usage: headless-session-test.lua <session-dir> <export-dir>")

local rate = 48000
local s = create_session (sdir, "smoke", rate)
assert (s, "create_session failed")
print ("backend: " .. AudioEngine:current_backend_name ())

local tl = Session:new_audio_track (1, 2, ARDOUR.RouteGroup (), 1, "Noise",
	ARDOUR.PresentationInfo.max_order, ARDOUR.TrackMode.Normal, true)
assert (tl:size () == 1, "new_audio_track failed")
local track = tl:front ()

local noise = ARDOUR.LuaAPI.new_luaproc (Session, "ACE Noise")
assert (not noise:isnil (), "ACE Noise Lua DSP not found")
assert (track:add_processor_by_index (noise, 0, nil, true) == 0, "add_processor failed")
-- "Noise Level" (control 0): -30 dBFS, so the export can be checked for it
assert (ARDOUR.LuaAPI.set_processor_param (noise, 0, -30), "set_processor_param failed")

-- two seconds of session range
Session:set_session_extents (Temporal.timepos_t (0), Temporal.timepos_t (2 * rate))
Session:save_state ("", false, false, false, false, false)

local n = 0
for r in Session:get_routes ():iter () do n = n + 1 end
print ("routes: " .. n)

local e = Session:simple_export ()
-- "WAV @ session-rate" (share/export/wav.preset): no normalization, so the
-- exported level reflects the -30 dBFS generator setting
assert (e:set_preset ("75969a1c-3133-4694-864b-a1fa50e43348"), "WAV export preset not found")
e:set_folder (edir)
e:set_name ("smoke")
e:set_range (0, 2 * rate)
assert (e:check_outputs (), "export: master bus has no outputs")
assert (e:run_export (), "export failed")
print ("export done")

-- drop all references to session objects before the session goes away,
-- otherwise the track would be destroyed by the Lua GC after the session
e = nil; noise = nil; track = nil; tl = nil
collectgarbage ()
close_session ()
print ("HEADLESS-SESSION-TEST-OK")
