# Haiven SDK for Unity

`com.haiven.sdk` is the Unity Package Manager package for the Haiven client:
game sign-in handoff and the WebGL socket bridge. The package also carries
the engine-free C# core as source in `com.haiven.sdk/Runtime/Core`, which
Unity compiles as the `Haiven.Sdk.Core` assembly. A project that uses the
package must not also import a prebuilt `Haiven.Sdk.Core` assembly.

Documentation: <https://docs.haiven.gg>. The Unity guide is
<https://docs.haiven.gg/engines/unity>. The `haiven` command-line tool is
<https://docs.haiven.gg/install/cli>.

The project you can open today is
[haiven-sdk-unity-bossroom](https://github.com/haiven-dev/haiven-sdk-unity-bossroom),
Unity's Boss Room sample with the Haiven demo packages embedded.
For an existing Unity project, see [Add the package to your own project](#add-the-package-to-your-own-project).

## Install Unity Hub and the Editor

1. Install [Unity Hub](https://unity.com/download) and sign in. A Personal
   license can activate the Editor.
2. Install Unity Editor **6000.0.52f1** (changeset `9e4086222921`). That is
   the editor pinned by `host/ProjectSettings/ProjectVersion.txt` in this
   repository and by `ProjectSettings` in haiven-sdk-unity-bossroom.
   `com.haiven.sdk/package.json` declares `2022.3` as the package minimum;
   6000.0.52f1 is the editor this repository's host and the demo are tested on.
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

## Install the haiven CLI

`haiven` is optional. You do not need it to open the Boss Room demo or to
add a published package. It is one static binary for Linux, macOS, and
Windows. Install, pin, and command notes are at
<https://docs.haiven.gg/install/cli>.

No `haiven` release is published yet. Use Unity Hub and the Editor for the
steps on this page until a release exists.

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

The demo reads each public setting from the Editor process environment,
then from the committed asset
`Assets/HaivenGenerated/Resources/Haiven/BossRoomDemoSettings.json`
(`schemaVersion` 1), then from a `.env` file in the project root (the
folder that contains `Assets`). A non-empty field in that asset is used
before `.env`. The Boss Room clone has no `Haiven/HaivenDemoConfiguration`
resource, so that file is not a source. Unity Hub does not pass variables
from a shell you export later, and it does not load `.env`. A stock Hub
open uses the asset. The production `.env` below does not configure that open
by itself.

The committed asset points to the local stack:

- `baseUrl` is `http://127.0.0.1:18480/v0`
- `realtimeUrl` is `ws://127.0.0.1:18480/v0/ws`
- `signInUrl` is `http://127.0.0.1:3000/connect/game`
- `redirectUri` is `http://127.0.0.1:47615/haiven/callback`

`appId`, `integrationId`, `communityId`, `channelId`, and `rewardRef` are
filled too. Play talks to those loopback hosts. Those required fields are
present, so the HUD does not show `CONFIG REQUIRED` and does not name the
variables in `.env`.

To make that `.env` apply, either:

- Put the variables in the Editor process environment before the Editor
  starts, and start the Editor from that process. Hub will not see an
  export made after it launched the Editor. A process value overrides the
  asset.
- Or keep opening the project from Hub, and clear the asset fields `.env`
  should fill. Set these strings to `""`, and leave `schemaVersion` at 1
  and `redirectUri` unchanged: `baseUrl`, `realtimeUrl`, `appId`,
  `integrationId`, `communityId`, `channelId`, `rewardRef`, and
  `signInUrl`. Save the file and let the Editor import it, then press Play.
  Empty fields then come from `.env`. Do not commit that edit.

Do not commit `.env`. Do not put an access token, an integration key, or
`HAIVEN_DEMO_ACCESS_TOKEN` in `.env` or in the asset. The player signs in
at runtime, and the token stays in memory.

Ask the Haiven app owner for the ids. Production hosts are below. The
integration must allow the redirect exactly, including the port. The
default, already stored in `redirectUri`, is
`http://127.0.0.1:47615/haiven/callback`. Use `127.0.0.1`, not
`localhost`.

```dotenv
HAIVEN_DEMO_BASE_URL=https://haiven.gg/v0
HAIVEN_DEMO_REALTIME_URL=wss://haiven.gg/v0/ws
HAIVEN_DEMO_APP_ID=<app id>
HAIVEN_DEMO_INTEGRATION_ID=<public integration id>
HAIVEN_DEMO_CHANNEL_ID=<channel id>
HAIVEN_DEMO_REWARD_REF=<reward ref>
```

`HAIVEN_DEMO_SIGN_IN_URL` is optional when `signInUrl` in the asset is
empty and the sign-in page shares the API host. In production that is
`https://haiven.gg/connect/game`. The shipped `signInUrl` blocks that
default, so the browser opens `http://127.0.0.1:3000/connect/game` until
the field is cleared or the Editor process sets the variable.
`HAIVEN_DEMO_COMMUNITY_ID` is optional and is the chat channel's
community. The shipped `communityId` is used until that field is empty or
the Editor process sets the variable.

Add the clone in Unity Hub, open it with **6000.0.52f1**, open
`Assets/Scenes/Startup.unity`, and press Play. If a required value is
still missing after the asset and `.env`, the HUD shows `CONFIG REQUIRED`
and names it.

## Add the package to your own project

### Release download

Download `com.haiven.sdk-0.1.0-preview.1.tgz` from the
[Unity SDK release](https://github.com/haiven-dev/haiven-sdk-unity/releases/tag/v0.1.0-preview.1).
Use **Package Manager → + → Add package from tarball** and select the file.
Verify the tarball with the release's `SHA256SUMS`.

### Tagged source

Add this package to the `dependencies` object in `Packages/manifest.json`.

```json
"com.haiven.sdk": "https://github.com/haiven-dev/haiven-sdk-unity.git?path=/com.haiven.sdk#v0.1.0-preview.1"
```

Open the project in Unity and commit `manifest.json` and `packages-lock.json`.
The UPM package includes the source core and the metadata Unity needs.

### Standalone .NET core

For a standalone .NET project that supports .NET Standard 2.1, download
`haiven-unity-core-portable.tar.gz` from the same release and extract
`Haiven.Sdk.Core.dll`. Add the DLL as an assembly reference. Its checksum is
in `SHA256SUMS.binaries`. Use the UPM package above for Unity projects.

## Releases

Releases are published on this repository's
[GitHub Releases page](https://github.com/haiven-dev/haiven-sdk-unity/releases).
This repository is published from Haiven's SDK source, and Haiven's release
pipeline builds and publishes every release from that source after a
maintainer review. Nothing in this repository cuts a release: there is no
release workflow, release pull request, or tag to push here.

Each release carries `com.haiven.sdk-<version>.tgz` and its digest in
`SHA256SUMS`. Releases with supplemental binaries include
`SHA256SUMS.binaries`. The release notes name the source commit.

Versions follow [Semantic Versioning](https://semver.org/). A release is
tagged `v<version>`, and `version` in the released package's `package.json`
carries the same number; the pipeline refuses to publish a release whose
`package.json` differs from its tag. `0.0.0` is the development placeholder
and is never released. Haiven's SDK and demo repositories share one version
line: the repositories in one release carry the same version, and a release
can cover only some of them, so this repository's version numbers can skip. A
version with a pre-release suffix (`v1.2.3-rc.1`) is published as a GitHub
pre-release and is never marked Latest. Leave the package version to Haiven's
release process; a pull request here does not choose a version.

Source updates arrive as pull requests into `main`. Contributions are
welcome as pull requests here too. Haiven's maintainers carry each accepted
change into Haiven's source, so later updates keep it.

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

Haiven source in this repository is licensed under the Apache License,
Version 2.0. See [LICENSE](LICENSE). Contributions are accepted under that
license, as [CONTRIBUTING.md](CONTRIBUTING.md) says.

<!-- features:start (generated by codegen/features.py; do not edit) -->

### Feature coverage

| Family | Unity |
|---|:---:|
| Envelope | ~ |
| Session lifecycle | ~ |
| Request recovery | ✅ |
| Open vocabularies | ~ |
| REST | ○ |
| Game login handoff | ○ |
| P2P sessions | ~ |
| API surface | ~ |
| Product | ~ |
| Developer experience | ~ |

✅ shipped · `↑` inherited from the language SDK this target ships, proven only in that SDK's runner and not inside the engine · `~` partial · `—` absent · `○` not yet proven by any scenario · `⊘` not applicable. A family cell is ✅ only when every counted row is ✅, and `↑` when every counted row is ✅ or `↑`; `MAY` requirements and rows marked optional are not counted. Every row: the full Haiven SDK feature matrix.

<!-- features:end -->
