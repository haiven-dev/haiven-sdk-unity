# Contributing

Contributions are welcome. This repository is public. Bug reports, fixes,
and documentation improvements are all useful. Contributions are accepted
under the repository license once it is recorded.

The UPM package is `com.haiven.sdk` at the root of this repository.

## Issues

Open a GitHub issue for a bug, a question about behavior, or a change you
want to discuss before writing it. Search open issues first.

Include the package version, the Unity editor version, and the steps that
show the problem. Do not paste access tokens, passwords, or private
endpoints.

## Pull requests

1. Fork the repository and branch from `main`.
2. Keep the change focused.
3. Use a [Conventional Commits](https://www.conventionalcommits.org/)
   subject:

   `type(scope): subject`

   `type` is one of `feat`, `fix`, `docs`, `deps`, `style`, `refactor`,
   `perf`, `test`, `build`, `ci`, `chore`, or `revert`. `scope` is
   optional.
4. Open the pull request against `main`. Say what changed and how you
   checked it.

Do not commit access tokens, passwords, private endpoints, or local
editor credentials.

## Checks

From the repository root, this checks the package layout without Unity:

```sh
node validate-package.mjs
```

It is not a substitute for opening the package in the editor. The host
project under `host/` names Unity `6000.0.52f1` in
`host/ProjectSettings/ProjectVersion.txt`. Editor and PlayMode tests live
in that host. Say which checks you ran.
