## 1. Implementation

- [x] 1.1 Add an exact legacy-path redirect to the canonical lowercase ST52 URL.
- [x] 1.2 Preserve query strings and avoid redirecting lowercase or unrelated landing paths.
- [x] 1.3 Add automated policy coverage.
- [x] 1.4 Add a post-deploy smoke assertion for the production redirect.

## 2. Verification and release

- [x] 2.1 Run frontend SEO tests, lint, and production build.
- [x] 2.2 Run shell syntax and strict OpenSpec validation.
- [x] 2.3 Pull/rebase, commit, push both repositories, and rebuild manual deployment artifacts.
- [ ] 2.4 Upload and apply the frontend release, then verify the public redirect.
