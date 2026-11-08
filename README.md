# Haiven SDK for Unity

`com.haiven.sdk` is the Unity Package Manager package for the Haiven client:
game sign-in handoff and the WebGL socket bridge. The package source in this
repository is the Unity bridge. The engine-free C# core is not in that folder.
A tagged release builds it from the `haiven-sdk-dotnet` commit named in
`ci/haiven-sdk-dotnet.ref` and attaches it next to the package.

Documentation: <https://docs.haiven.gg>. The Unity guide is
<https://docs.haiven.gg/engines/unity>. The `haiven` command-line tool is
<https://docs.haiven.gg/install/haiven-cli>. `docs.haiven.gg` is the
production host. Until it is published, the same paths are served at
<https://docs.sbx.haiven.gg>.

The project you can open today is
[haiven-sdk-unity-bossroom](https://github.com/haiven-dev/haiven-sdk-unity-bossroom):
Unity's Boss Room sample with the Haiven demo packages embedded. This
repository has no GitHub release yet. `com.haiven.sdk/package.json` is
`0.0.0`, and the release workflow will not tag that version.

## Install Unity Hub and the Editor

1. Install [Unity Hub](https://unity.com/download) and sign in. A Personal
   license can activate the Editor.
2. Install Unity Editor **6000.0.52f1** (changeset `9e4086222921`). That is
   the editor pinned by `host/ProjectSettings/ProjectVersion.txt` in this
   repository and by `ProjectSettings` in haiven-sdk-unity-bossroom.
   `com.haiven.sdk/package.json` declares `6000.0` as the package minimum.
   Install that patch from
   [the 6000.0.52f1 editor archive](https://unity.com/releases/editor/whats-new/6000.0.52f1)
   if Hub does not list it. Include a desktop build-support module for the
   platform you play on. The test host in this repository also expects the
   WebGL module; see `host/README.md`.
3. [Git](https://git-scm.com/) must be on `PATH`. The Boss Room demo also
   needs [Git LFS](https://git-lfs.com/).

Open a project from Hub with **Projects**, then **Add** (or **Add project
from disk**), and choose the folder that contains `Assets`, `Packages`, and
`ProjectSettings`. Select editor `6000.0.52f1` when Hub asks. The first
import is slow.

## Install haiven-cli

`haiven` is optional. You do not need it to open the Boss Room demo or to
add a published package. It is one static binary for Linux, macOS, and
Windows. Full install, pin, and command notes are at
<https://docs.haiven.gg/install/haiven-cli>.

Linux and macOS:

```sh
curl -fsSL https://raw.githubusercontent.com/haiven-dev/haiven-cli/main/scripts/install.sh | sh
```

Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/haiven-dev/haiven-cli/main/scripts/install.ps1 | iex
```

The scripts install `haiven` to `~/.local/bin` on Linux and macOS, and to
`%LOCALAPPDATA%\haiven\bin` on Windows. Open a new terminal and run
`haiven version`.

No `haiven` release is published, and the haiven-cli source repository is
not public. Those commands do not install a binary today. Use Unity Hub and
the Editor for the steps on this page until a release exists.

## Open haiven-sdk-unity-bossroom

Clone Haiven's Boss Room repository. Do not download the
Unity-Technologies Boss Room archive. That archive does not contain the
Haiven packages.

```sh
git lfs install
git clone https://github.com/haiven-dev/haiven-sdk-unity-bossroom.git
```

`ProjectSettings` is at the clone root. The embedded packages are
`Packages/com.haiven.sdk` and `Packages/com.haiven.demo.bossroom`. The demo
package is moderated chat, a live reward claim, and inventory fed by Haiven
item entitlements. Boss Room's own license stays in that repository's
`LICENSE.md`.

The demo reads public project settings from the environment of the Editor
process, then from a generated settings asset, then from a `.env` file in
the project root (the folder that contains `Assets`). A `.env` file is the
reliable way to configure a project opened from Unity Hub, because Hub does
not inherit a shell you export later. Do not commit `.env`. Do not put an
access token, an integration key, or `HAIVEN_DEMO_ACCESS_TOKEN` in it. The
player signs in at runtime, and the token stays in memory.

Ask the Haiven app owner for the ids. Sandbox hosts are below. The
integration must allow the redirect exactly, including the port. The default
is `http://127.0.0.1:47615/haiven/callback`. Use `127.0.0.1`, not
`localhost`.

```dotenv
HAIVEN_DEMO_BASE_URL=https://sbx.haiven.gg/v0
HAIVEN_DEMO_REALTIME_URL=wss://sbx.haiven.gg/v0/ws
HAIVEN_DEMO_APP_ID=<app id>
HAIVEN_DEMO_INTEGRATION_ID=<public integration id>
HAIVEN_DEMO_CHANNEL_ID=<channel id>
HAIVEN_DEMO_REWARD_REF=<reward ref>
```

`HAIVEN_DEMO_SIGN_IN_URL` is optional when the sign-in page shares the API
host. For the sandbox that is `https://sbx.haiven.gg/connect/game`.
`HAIVEN_DEMO_COMMUNITY_ID` is optional and is the chat channel's community.

Add the clone in Unity Hub, open it with **6000.0.52f1**, open
`Assets/Scenes/Startup.unity`, and press Play. If a required variable is
missing, the HUD shows `CONFIG REQUIRED` and names it.

## Add the package to your own project

Not yet. Two release pieces are missing from a git install of this
repository:

- `com.haiven.sdk/` has no `.meta` files. Unity does not generate them for
  a git or tarball package, and it ignores assets that have none. The
  release build writes those files into `com.haiven.sdk-<version>.tgz` and
  `com.haiven.sdk-<version>.unitypackage`.
- The bridge calls types that live in the C# core (`IHaivenSocket` and the
  handoff types). That core, and the `System.Text.Json` assemblies it needs,
  ship as `haiven-sdk-core-<version>-netstandard2.1.zip` on the same release.
  Extract it into `Assets/Plugins`. The package folder does not contain
  those DLLs. `com.haiven.sdk/README.md` still shows an old `sdk-spike` git
  URL. Do not use that URL.

When a release exists, its tag is `v` plus the `version` in
`com.haiven.sdk/package.json` (for example `v0.1.0`, not `v0.0.0`). In
Unity Hub, open your project with **6000.0.52f1**. Then either:

- **Package Manager → + → Add package from tarball**, and choose
  `com.haiven.sdk-<version>.tgz`, or
- **Assets → Import Package → Custom Package**, and choose
  `com.haiven.sdk-<version>.unitypackage`. That imports an embedded package
  at `Packages/com.haiven.sdk/`. Do not import both.

Check `SHA256SUMS` from the release before you install. Commit the package
files or manifest entry the Editor writes. Install a release tag's
archives. A git URL, including a commit on this repository today, is not an
install: the `.meta` files are still absent. Do not pin a branch name.

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before
opening a pull request. From the repository root, this checks the package
layout without Unity:

```sh
node validate-package.mjs
```

That check is not a substitute for opening the package in the Editor. Say
which checks you ran. Do not commit access tokens, passwords, private
endpoints, or local editor credentials.

This repository does not yet have a license file. Contributions are accepted
under the repository license once that file is recorded, as
[CONTRIBUTING.md](CONTRIBUTING.md) says.
