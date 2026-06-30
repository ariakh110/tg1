## 1. Backend
- [x] 1.1 `AssistantSettings.lead_capture_mode` (off/soft/strict, default soft) + migration `0004`
- [x] 1.2 `ai.py::_lead_capture_block` + inject into `_build_system_prompt(cfg, chunks, conversation)`; thread mode through `run_chat`
- [x] 1.3 `tools.py::execute_tool(lead_gate=…)` gates `get_price_quote` in strict mode; `capture_lead` validates name + Iranian mobile and normalizes
- [x] 1.4 `capture_lead` schema requires `name`; serializer exposes `lead_capture_mode`

## 2. Frontend
- [x] 2.1 `AssistantPanel` mode selector (off/soft/strict)

## 3. Verification
- [x] 3.1 `assistant/tests.py` (10): phone validation/normalization, strict price gate on/off, prompt block per mode, already-captured note
- [x] 3.2 `manage.py check` + `test assistant` green; frontend ESLint clean
