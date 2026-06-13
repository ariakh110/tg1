## 1. Backend (tg1)
- [x] 1.1 `SiteSettings.head_scripts` + `footer_scripts` TextFields + migration `0006`
- [x] 1.2 Serializer exposes both fields; PATCH saves them (no length cap)
- [x] 1.3 `manage.py check`

## 2. Frontend (kavehmetal)
- [x] 2.1 `RawScripts` client injector (recreates real <script>; head vs body target)
- [x] 2.2 `getServerSettings` returns headScripts/footerScripts; layout injects head→`<head>`, footer→end of `<body>`
- [x] 2.3 SettingsProvider exposes both; SettingsPanel adds two textareas + save payload

## 3. Verification
- [x] 3.1 `npx eslint`; `npm run build` compiles
- [x] 3.2 `openspec validate add-custom-head-footer-scripts --strict`
- [ ] 3.3 After deploy: admin pastes a Clarity snippet in Header → it loads on every page; footer snippet loads before `</body>`; empty fields inject nothing
