## 1. Diagnosis and implementation

- [x] 1.1 Compare DNS, CDN, origin-IP, canonical Host, and arbitrary Host responses.
- [x] 1.2 Add a canonical-host policy and production Next.js middleware.
- [x] 1.3 Preserve paths and queries and reject unsafe methods on unexpected Hosts.

## 2. Verification and operations

- [x] 2.1 Add unit coverage for canonical, IP, `www`, arbitrary, spoofed-forwarded, and local-development Hosts.
- [x] 2.2 Add an origin-IP redirect assertion to the manual post-deploy smoke tests.
- [x] 2.3 Exclude the ignored design-sync bundle from source lint, then run frontend tests, lint/build, live production-server Host probes, shell validation, and strict OpenSpec validation.
- [x] 2.4 Pull/rebase, commit, push both repositories, and rebuild manual deployment artifacts.
