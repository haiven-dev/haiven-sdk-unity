# Haiven SDK for Unity

`com.haiven.sdk` — the Haiven client SDK as a UPM package.

## Installing

Add it by git URL in the Package Manager, or in `Packages/manifest.json`:

```json
{
  "dependencies": {
    "com.haiven.sdk": "https://github.com/haiven-dev/haiven-sdk-unity.git?path=com.haiven.sdk"
  }
}
```

Minimum editor version is `6000.0` (Unity 6.0 LTS). The package still targets
`netstandard2.1` and the WebGL `.jslib` plugin layout. The host pins editor
`6000.0.52f1`.

## Choosing a socket

The SDK takes an `IHaivenSocket` rather than opening one. Unity's supported
targets do not agree that sockets exist, so this is the one thing a host has to
supply:

| target | implementation |
|---|---|
| WebGL player | `WebGlSocket` — the browser's WebSocket, over the bundled `.jslib` |
| desktop / mobile IL2CPP, and the editor | your own over `System.Net.WebSockets` |

`WebGlSocket` compiles only under `UNITY_WEBGL && !UNITY_EDITOR`. The editor is
excluded on purpose: it runs Mono against the desktop socket stack even when the
build target is WebGL, so including it there would exercise the one path that is
never shipped.

## Game login handoff

`HandoffCoordinator` opens Haiven's first-party `/connect/game` page, validates
the returned state, exchanges the one-use code with S256 PKCE, and gives the
host an opaque access token plus its absolute expiry. The game owns every
platform-sensitive boundary:

```csharp
var tokens = new MemoryHandoffTokenStore();
var coordinator = new HandoffCoordinator(
    new HandoffOptions(
        new Uri("https://app.haiven.gg/connect/game"),
        new Uri("https://api.haiven.gg/v0/auth/handoff/exchange"),
        "your-public-integration-id",
        new Uri("your-game://haiven/callback")),
    new UnityHandoffBrowser(),
    new MemoryHandoffTransactionStore(),
    tokens,
    new UnityHandoffHttpTransport(),
    new UnityHandoffDispatcher());

var receiver = gameObject.AddComponent<HandoffDeepLinkReceiver>();
receiver.Configure(coordinator);
coordinator.Completed += credential => StartGameSession(
    credential.AccessToken,
    credential.ExpiresAt);
coordinator.Failed += error => ShowLoginError(error.Message);
coordinator.BeginLogin();
```

Create `UnityHandoffDispatcher` on Unity's main thread. The receiver subscribes
to `Application.deepLinkActivated`; if the game was launched from a deep link,
the host should also pass the initial callback URL to `receiver.Receive(...)`.
For WebGL, deliver the configured web callback the same way from the host page.
`UnityHandoffHttpTransport` uses an explicit form body and `UnityWebRequest`, so
the exchange does not depend on `HttpClient`, threads, or a native socket stack.

The included transaction store is deliberately memory-only: the verifier is
one-use, is removed before exchange, and expires locally after 15 minutes. The
included token store also keeps the credential only in memory. A game that
needs persistence supplies `IHandoffTokenStore` backed by its platform's secure
credential store; do not put the bearer in `PlayerPrefs`. The handoff has no
client secret and returns no refresh token. On expiry, begin login again.

## A JSON reader is not bundled

`System.Text.Json` is not in the `netstandard2.1` surface, and this package does
not carry a copy. A consumer inherits the dependency or supplies its own reader.

That is deliberate rather than unfinished. Picking a JSON library for a game
project is a decision with consequences for build size and IL2CPP stripping that
belong to the project, not to an SDK it depends on.

**`UnityEngine.JsonUtility` is not a safe default here, and the reason is
protocol-level.** The two outbound frame shapes are told apart by the *presence*
of `success`, not its value. `JsonUtility` is documented to map an absent field
to the type's default, and `bool` defaults to `false` — which would make every
server-initiated event read as a *failed reply*. The C# spike hit exactly this
and had to use `bool?` with `TryGetProperty` to get presence back. Whether
`JsonUtility` can express the distinction at all is **unmeasured** — see below.

## What here is unverified

There is no Unity installation in this repository, so **nothing in this package
has been opened in the editor or built for a player.** The layout follows
documented UPM and IL2CPP conventions and `../validate-package.mjs` checks the
mechanical half of that, but a rule with one right answer is not the same as a
build that ran.

Three things need a real Unity project before they should be trusted:

1. **The `.jslib` interop.** The callback signatures, `makeDynCall` usage, and
   the `_malloc`/`_free` handoff are written from the emscripten conventions
   Unity documents. None of it has round-tripped a frame.
2. **`link.xml`.** Confirm it by *removing* it and watching a WebGL build break.
   A `link.xml` that was never needed and one that works look identical.
3. **`JsonUtility`.** Whether it can represent the presence discriminant at all,
   and what a consumer that reaches for it first will actually observe.

The engine harness additionally contains EditMode dispatcher coverage, a
PlayMode deep-link completion test, and a built-player WebGL exchange against a
loopback HTTP fixture. They remain evidence only after the activated Unity
runner described in `../host/README.md` executes them.
