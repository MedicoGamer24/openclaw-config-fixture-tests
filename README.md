# Disposable OpenClaw configuration fixtures

Generic integration experiment for a NEW public repository. No production data,
configuration, paths, credentials, reports or service are included. It tests official
CLI preconditions, dry-run, apply/rollback, backups and a small cooperative journal.
It is not a production guardian implementation or a repair for authentication errors.

Only manually dispatch the single workflow on a GitHub-hosted standard `macos-26`
ARM64 runner. The public-repository condition fails closed for a private repository.
One job, timeout 15 minutes, no scheduled triggers, artifacts, caches, deployments,
OIDC or secret inputs. Checkout has contents:read and does not persist credentials.
Standard hosted runners for public repositories have free compute under GitHub's
published terms; never substitute larger/self-hosted/private runners or paid services.

The future job creates `/Users/fixture-user` only if absent on a fresh runner. This
is a fabricated user directory, not a mounted personal home. It installs official
Node 26.8.1 and OpenClaw 2026.10.4. The Node archive is checked against its published
SHA256, the OpenClaw tarball against the published SHA512 SRI. Lifecycle scripts,
including deferred lifecycle on CLI startup, are explicitly part of installation:
they may download a native fs-safe addon and prune package files. No optional native
dependencies are intentionally omitted. Transitive provenance is NOT fully audited.
The npm publication provenance source commit may differ from the release tag; the
published tarball integrity, not a source checkout, defines this experiment's input.

No Gateway is started. All config values are fabricated. Subprocesses get a literal
environment, not repository secrets or the checkout token. Network access remains
available; this is NOT a network sandbox. Raw CLI/install streams, fixture config,
backups and audit files are never uploaded. Only fixed checks and boolean results
reach logs. A dry-run assertion only covers config bytes, not all bootstrap effects.

The journal is single-threaded and advisory between cooperating processes on the
same persistent lock inode. Interruption after `started` is uncertain and never
retried automatically. Tests use actual child processes and controlled interleavings.
Special-ACL refusal is an admission test, not proof that the official writer preserves
ACLs. macOS image/hardware differ from any particular production machine. Passing
this suite does not authorize deployment or certify a production configuration.

Official references:
- https://nodejs.org/en/blog/release/v26.8.1
- https://registry.npmjs.org/openclaw/2026.10.4
- https://github.com/actions/checkout/commit/11bd71901bbe5b1630ceea73d27597364c9af683
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners

No official integration result exists yet. Local checks only exercise fabricated
journal files and statically inspect the proposed workflow and integration code.
