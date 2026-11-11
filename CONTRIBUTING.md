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
it. Ready work lands on `main` only through the promotion dispatch
below, and then through the Release Please pull request that follows.

Do not commit access tokens, passwords, private endpoints, or local
editor credentials.

## sdk-dev flow

`sdk-dev` takes ready work. Squash-merge those pull requests. The pull
request title becomes the commit, and it has to be a conventional
commit, because that subject is what the promotion records.

`main` is what gets released. Release Please
(`.github/workflows/release-please.yml`) runs on `main` only. It cannot
use `sdk-dev` as its source while opening a release pull request against
`main`, so a reviewed promotion lands `sdk-dev` on `main` first.

Topic branches carry unready work. Update them by rebasing onto
`sdk-dev`.

### Promotion dispatch

Dispatch the `promote sdk-dev` workflow
(`.github/workflows/promote-sdk-dev.yml`) by hand from `main`, the ref
that contains that file. Pass `expected_sdk_dev_sha`: the full lowercase
40-character `sdk-dev` head to promote. The run stops if `sdk-dev` has
moved, if `main` is not an ancestor of `sdk-dev`, or if that range has
no commits.

```sh
git fetch origin
gh workflow run "promote sdk-dev" --ref main \
  -f expected_sdk_dev_sha="$(git rev-parse origin/sdk-dev)"
```

The workflow publishes a disposable branch `promote/sdk-dev-<sha>` at
that exact commit and opens or refreshes a pull request titled
`chore: promote sdk-dev to main` against `main`. It does not merge. It
does not delete or reset `sdk-dev`. It closes older open
`promote/sdk-dev-*` pull requests and leaves their branches in place.
The disposable head may be deleted on merge. `sdk-dev` is not.

The pull request body lists the range inside `BEGIN_COMMIT_OVERRIDE`.
Each commit is a `BEGIN_NESTED_COMMIT` that keeps the subject and any
`BREAKING CHANGE:`, `BREAKING-CHANGE:`, or `Release-As:` line. Squash-merge
the promotion. Release Please reads that block in place of the squash
commit. The `chore` title stays out of the changelog.

After the promotion merges, Release Please opens the version and
changelog pull request against `main`. Merging that pull request tags
`v<version>` and publishes the GitHub release.

### Reset steps

Reset `sdk-dev` to `main` only after the release pull request has
merged, not after the promotion. `main` then has the squashed promotion
and the Release Please version bump, and one reset covers both. The
promotion workflow never performs this reset.

`<promoted-sdk-dev-sha>` is the `sdk-dev` head the promotion recorded
(`expected_sdk_dev_sha`). Guard the force-with-lease with that sha:

```sh
git fetch origin
git push --force-with-lease=sdk-dev:<promoted-sdk-dev-sha> origin origin/main:refs/heads/sdk-dev
```

If anything landed on `sdk-dev` after that sha, the lease refuses the
push. Replay only the newer commits, then push with a lease on the
current `sdk-dev` head:

```sh
git rebase --onto origin/main <promoted-sdk-dev-sha> origin/sdk-dev
git push --force-with-lease=sdk-dev:<current-sdk-dev-sha> origin HEAD:refs/heads/sdk-dev
```

Move an open topic branch onto the new `sdk-dev` with
`git rebase --onto origin/sdk-dev <old-sdk-dev-sha>`.

## Checks

From the repository root, this checks the package layout without Unity:

```sh
node validate-package.mjs
```

It is not a substitute for opening the package in the editor. The host
project under `host/` names Unity `6000.0.52f1` in
`host/ProjectSettings/ProjectVersion.txt`. Editor and PlayMode tests live
in that host. Say which checks you ran.
