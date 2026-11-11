# Unity engine test host

This host consumes `file:../../com.haiven.sdk` through UPM. That path is
relative to `host/Packages` and resolves to `com.haiven.sdk` at the root of
this repository. The package compiles both the Unity bridge (`Haiven.Sdk`) and
the portable core (`Haiven.Sdk.Core`) from source under `Runtime/` and
`Runtime/Core`. Do not publish `Haiven.Sdk.Core.dll` or its NuGet neighbors
into `host/Assets/Plugins`: Unity rejects a precompiled assembly and an
assembly definition that share the name `Haiven.Sdk.Core`. No replacement
socket or fake Unity API is compiled into this host.

## Runner setup and activation

Use an activated Linux **Unity 6000.0.52f1 (9e4086222921)** editor with the matching
**WebGL Build Support** module. Point `UNITY_EDITOR` at that editor binary.
The runner accepts only the version string `6000.0.52f1`. The matching module
includes Unity's IL2CPP/Emscripten toolchain. The engine checks both its version
and module availability before the build. [Official editor and module downloads](https://unity.com/releases/editor/whats-new/6000.0.52f1).

Register an isolated self-hosted runner with labels `linux`, `x64`, and
`unity-6000.0.52f1-webgl`. Activate the editor under the same OS account that runs
the Actions agent using your organization's Unity entitlement; verify an editor
launch succeeds under that account. Credentials belong in the runner's license
service or the local secret store, not this repository or command logs. Install Python 3,
Node 24, the .NET SDK pinned by `haiven-sdk-dotnet/global.json`, and Chromium's
system dependencies (Playwright `install-deps chromium` during runner provisioning).

No SDK runner or Unity activation secret was available when this harness was
added. The workflow therefore has explicit dispatch/reusable triggers for its
first validation run. It is **not yet a mandatory PR gate**. After provisioning,
run it on this branch, fix any real engine failures, then enable PR/main-push
triggers and require its status check. Do not count static checks as engine proof.

## Run

```sh
npm ci --prefix ci
(cd ci && npx --no-install playwright install chromium)
UNITY_EDITOR=/path/to/Unity python3 ci/run.py
```

Run from the repository root. `UNITY_EDITOR` is the 6000.0.52f1 editor binary.
Logs and NUnit XML remain in `build/unity-results/`.
Without that editor, the layout checks in this repository still run:

```sh
node validate-package.mjs
python3 -m unittest ci.test_reports
```

`.github/workflows/build.yml` runs those two on pull requests and on `v*` tags.
`.github/workflows/release.yml` builds the release assets when a `v*` tag is
pushed. The tag must be `v` plus `com.haiven.sdk/package.json`'s version, and
`0.0.0` is refused.
An editor run uploads its logs even on failure. Each editor test process gets 15
minutes, the build 30 minutes, and the browser three minutes; the job gets an
hour. Missing editors, wrong versions, absent/empty/duplicate/skipped/failed
expected cases, unsuccessful builds, or absent browser completion fail.

EditMode asserts local package registration, refused-reply/event presence, and
main-thread dispatch. PlayMode makes two real `SystemNetSocket` connections,
observes callbacks, sends a Unicode frame, and disposes each connection. It also
delivers an auth callback through `HandoffDeepLinkReceiver` after an asynchronous
exchange and requires token storage and completion on Unity's main thread. The
socket case is transport reconnection; the C# core does not yet provide a
higher-level Session state machine.

The release WebGL player uses **High managed stripping** and the package's
actual editor-excluded `.jslib` bridge. Chromium requires a real Unicode socket
round trip, protocol parsing, server-observed disposal, and a real
`UnityWebRequest` form exchange before closing its page. The fixture rejects
missing or extra auth fields, including client-secret-shaped additions, and the
player requires the returned token and main-thread completion. A Unity log line
alone cannot pass it. The loopback fixture binds only 127.0.0.1:18765. Browser
and editor runs are serialized per repository.

Engine execution and the first built-player run remain unverified until the
activated runner exists. `link.xml` necessity is not established merely by a
successful build: a removal experiment remains part of engine validation.
