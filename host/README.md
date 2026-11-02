# Unity engine test host

This host consumes `file:../../com.haiven.sdk` through UPM and the current
C# core built from `csharp/Haiven.Sdk/*.cs`. The package currently contains only
the bridge: preparation supplies `Haiven.Sdk.Core.dll` and its pinned
System.Text.Json dependencies as host plugins. No replacement socket or fake
Unity API is compiled into this host.

## Runner setup and activation

Use an activated Linux **Unity 2022.3.62f2 (7670c08855a9)** editor with the matching
**WebGL Build Support** module, installed at
`/opt/unity/2022.3.62f2/Editor/Unity`. The matching module includes Unity's
IL2CPP/Emscripten toolchain. The engine checks both its version and module
availability before the build. [Official editor and module downloads](https://unity.com/releases/editor/whats-new/2022.3.62f2).

Register an isolated self-hosted runner with labels `linux`, `x64`, and
`unity-2022.3.62f2-webgl`. Activate the editor under the same OS account that runs
the Actions agent using your organization's Unity entitlement; verify an editor
launch succeeds under that account. Credentials belong in the runner's license
service or passage, not this repository or command logs. Install Python 3,
Node 24, .NET SDK 10.0.400 (see `global.json`), and Chromium's system dependencies (Playwright
`install-deps chromium` during runner provisioning).

No SDK runner or Unity activation secret was available when this harness was
added. The workflow therefore has explicit dispatch/reusable triggers for its
first validation run. It is **not yet a mandatory PR gate**. After provisioning,
run it on this branch, fix any real engine failures, then enable PR/main-push
triggers and require its status check. Do not count static checks as engine proof.

## Run

```sh
npm ci --prefix csharp/unity/ci
(cd csharp/unity/ci && npx --no-install playwright install chromium)
UNITY_EDITOR=/opt/unity/2022.3.62f2/Editor/Unity python3 csharp/unity/ci/run.py
```

Run from the SDK root. Logs and NUnit XML remain in `build/unity-results/`.
The workflow uploads them even on failure. Each editor test process gets 15
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
