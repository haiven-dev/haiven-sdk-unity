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

1. Fork the repository and branch from `sdk-dev`.
2. Keep the change focused.
3. Use a [Conventional Commits](https://www.conventionalcommits.org/)
   subject:

   `type(scope): subject`

   `type` is one of `feat`, `fix`, `docs`, `deps`, `style`, `refactor`,
   `perf`, `test`, `build`, `ci`, `chore`, or `revert`. `scope` is
   optional.
4. Open the pull request against `sdk-dev`. Say what changed and how you
   checked it.

`main` is the release branch. Do not open feature pull requests against
it. Ready work reaches `main` only through the promotion pull request
below, and is released through the Release Please pull request that
follows.

Do not commit access tokens, passwords, private endpoints, or local
editor credentials.

## sdk-dev flow

`sdk-dev` takes ready work. Squash-merge those pull requests. The pull
request title becomes the commit, and it has to be a conventional
commit, because that subject is what the promotion lists and what
Release Please reads.

`main` is what gets released. Release Please
(`.github/workflows/release-please.yml`) runs on `main` only, so the
promotion lands `sdk-dev` on `main` first.

Topic branches carry unready work. Update them by rebasing onto
`sdk-dev`.

### Promotion pull request

The `Promotion PR` workflow (`.github/workflows/promotion-pr.yml`) keeps
one open pull request from `sdk-dev` into `main`, titled
`chore: promote sdk-dev into main`. Its description lists the commits
`sdk-dev` carries that `main` lacks, grouped into breaking changes,
features, bug fixes, and other changes. The workflow runs on every push
to `sdk-dev` or `main` and can also be dispatched by hand. It rewrites
only the generated block between its markers, so notes added outside
that block are kept. It does not push branches, merge, version, tag, or
release.

The pull request head is `sdk-dev` itself. Review it like any other pull
request, then merge it with **Create a merge commit**, not squash or
rebase. `main` then holds each `sdk-dev` commit, Release Please reads
them individually, and the next promotion lists only newer commits.

### Release

After the promotion merges, Release Please opens the version and
changelog pull request against `main`. Merging that pull request tags
`v<version>` and publishes the GitHub release; the `Release` workflow
then attaches the package assets.

The first release is `v0.0.1`. It comes from `initial-version` in
`release-please-config.json`, because `.release-please-manifest.json`
records no earlier release (`0.0.0`). Its release pull request sets
`com.haiven.sdk/package.json` `version` to `0.0.1`, replacing the
`0.1.0-preview.1` that `sdk-dev` declares. To ship a different first
version, change `initial-version` before the first promotion merges.
After the first release, Release Please takes the version from the
manifest and the commits.

Merge nothing into `sdk-dev` from the promotion merge until the release
pull request merges. Release Please reads `main` back to the latest
release and stops there. A commit that `sdk-dev` took before the release
merged is older than the release, so the next promotion brings it to
`main` but Release Please never reads it, and it misses `CHANGELOG.md`
and the version bump. If Release Please opens no release pull request
for a promotion, because it holds only hidden types such as `ci`,
`chore`, and `test`, there is no release to wait for and no hold.

If a commit lands in that window anyway, add an override block to the
next promotion pull request's description, outside the generated block,
before that promotion merges. List each commit that landed in the window
by its conventional subject:

```text
BEGIN_COMMIT_OVERRIDE
fix(scope): subject of the first missed commit

feat(scope): subject of the second missed commit
END_COMMIT_OVERRIDE
```

Release Please reads the block in place of the promotion's merge commit
message, so the listed commits reach the next release. List only the
commits from the window; Release Please reads later commits on its own.

### Back-merge

After the release pull request merges, merge `main` back into `sdk-dev`
with a merge commit so `sdk-dev` carries the version bump and
`CHANGELOG.md`. Merge commits are left out of the promotion list, so
this does not show up in the next promotion.

```sh
gh pr create --base sdk-dev --head main \
  --title "chore: merge main back into sdk-dev" \
  --body "Back-merge after the release."
```

Merge that pull request with **Create a merge commit**. `sdk-dev` is
never reset or force-pushed, so open topic branches need no special
handling.

## Checks

From the repository root, this checks the package layout without Unity:

```sh
node validate-package.mjs
```

It is not a substitute for opening the package in the editor. The host
project under `host/` names Unity `6000.0.52f1` in
`host/ProjectSettings/ProjectVersion.txt`. Editor and PlayMode tests live
in that host. Say which checks you ran.
