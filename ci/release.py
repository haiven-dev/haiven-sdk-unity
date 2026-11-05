#!/usr/bin/env python3
"""Build the GitHub release assets for com.haiven.sdk.

Produces, in --out:

  com.haiven.sdk-<version>.tgz            UPM tarball (npm-pack layout, root package/)
  com.haiven.sdk-<version>.unitypackage   the same package, rooted at Packages/com.haiven.sdk/
  Haiven.Sdk.Core.dll / .pdb              the engine-free C# core, netstandard2.1
  haiven-sdk-core-<version>-netstandard2.1.zip
                                          the core plus the System.Text.Json closure it
                                          needs, i.e. what a project drops into Assets/Plugins
  SHA256SUMS                              sha256sum-format digests of every file above

The Unity bridge assembly (Haiven.Sdk, Runtime/Haiven.Sdk.asmdef) is NOT built
here: it references UnityEngine, and Unity's managed assemblies are not
redistributable. It ships as source inside the package and Unity compiles it.

Every archive is reproducible: entries are sorted, owners are 0, modes are
fixed, and timestamps come from SOURCE_DATE_EPOCH or the HEAD commit time.

  python3 ci/release.py --out build/release [--tag v1.2.3] [--dotnet-sdk ../haiven-sdk-dotnet]
"""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = ROOT / "com.haiven.sdk"
CORE_PROJECT = ROOT / "core" / "Haiven.Sdk.Core.csproj"
NAME = "com.haiven.sdk"
# SemVer with an optional prerelease (0.1.0-alpha.1). 0.0.0 is legal in
# package.json; resolve_version refuses to tag that development sentinel.
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


class ReleaseError(Exception):
    pass


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True)


def source_date_epoch():
    if os.environ.get("SOURCE_DATE_EPOCH"):
        return int(os.environ["SOURCE_DATE_EPOCH"])
    return int(git("log", "-1", "--format=%ct").strip())


def resolve_version(tag):
    manifest = json.loads((PACKAGE_DIR / "package.json").read_text())
    version = manifest.get("version", "")
    if manifest.get("name") != NAME:
        raise ReleaseError(f"package.json name is {manifest.get('name')!r}, expected {NAME!r}")
    if not SEMVER.match(version):
        raise ReleaseError(f"package.json version {version!r} is not MAJOR.MINOR.PATCH[-PRERELEASE]")
    if tag:
        if not tag.startswith("v") or not SEMVER.match(tag[1:]):
            raise ReleaseError(f"tag {tag!r} is not vMAJOR.MINOR.PATCH[-PRERELEASE]")
        if tag[1:] != version:
            raise ReleaseError(
                f"tag {tag} does not match com.haiven.sdk/package.json version {version}; "
                f"bump package.json to {tag[1:]} on main before tagging")
        if version == "0.0.0":
            raise ReleaseError("0.0.0 is a development sentinel and must not be tagged")
    return version


# --- package contents and .meta files ---------------------------------------
#
# Unity treats a package installed from a git URL, a registry, or a tarball as
# immutable and refuses to generate .meta files for it: any asset without one
# is ignored with "has no meta file, but it's in an immutable folder". The
# repository carries no .meta files today, so they are generated here. The GUID
# is derived from the package-relative path, which keeps it stable across
# releases (a reference a project makes to an asset in 0.1.0 still resolves in
# 0.2.0). A tracked .meta, if one is ever committed, always wins.

def package_files():
    tracked = git("ls-files", "-z", "--", str(PACKAGE_DIR.relative_to(ROOT))).split("\0")
    files = sorted(Path(p).relative_to(PACKAGE_DIR.relative_to(ROOT)).as_posix() for p in tracked if p)
    if not files:
        raise ReleaseError("no tracked files under com.haiven.sdk/")
    return files


def guid_for(rel):
    return hashlib.md5(f"{NAME}/{rel}".encode()).hexdigest()


def generated_meta(rel, is_dir):
    guid = guid_for(rel)
    head = f"fileFormatVersion: 2\nguid: {guid}\n"
    tail = "  userData: \n  assetBundleName: \n  assetBundleVariant: \n"
    if is_dir:
        return head + "folderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n" + tail
    suffix = Path(rel).suffix
    if suffix == ".cs":
        return head + ("MonoImporter:\n  externalObjects: {}\n  serializedVersion: 2\n"
                       "  defaultReferences: []\n  executionOrder: 0\n  icon: {instanceID: 0}\n") + tail
    if suffix == ".asmdef":
        return head + "AssemblyDefinitionImporter:\n  externalObjects: {}\n" + tail
    if rel == "package.json":
        return head + "PackageManifestImporter:\n  externalObjects: {}\n" + tail
    if suffix == ".jslib":
        # A .jslib is only meaningful in a WebGL player; say so explicitly
        # instead of relying on folder-name inference.
        return head + (
            "PluginImporter:\n  externalObjects: {}\n  serializedVersion: 2\n  iconMap: {}\n"
            "  executionOrder: {}\n  defineConstraints: []\n  isPreloaded: 0\n  isOverridable: 0\n"
            "  isExplicitlyReferenced: 0\n  validateReferences: 1\n  platformData:\n"
            "  - first:\n      Any: \n    second:\n      enabled: 0\n      settings: {}\n"
            "  - first:\n      Editor: Editor\n    second:\n      enabled: 0\n"
            "      settings:\n        DefaultValueInitialized: true\n"
            "  - first:\n      WebGL: WebGL\n    second:\n      enabled: 1\n      settings: {}\n") + tail
    if suffix in {".md", ".xml", ".txt", ".json"}:
        return head + "TextScriptImporter:\n  externalObjects: {}\n" + tail
    return head + "DefaultImporter:\n  externalObjects: {}\n" + tail


def package_entries():
    """(relative path, bytes or None for a folder, meta text) for every asset and folder."""
    files = package_files()
    assets = [f for f in files if not f.endswith(".meta")]
    tracked_meta = {f[:-len(".meta")] for f in files if f.endswith(".meta")}
    folders = sorted({p.as_posix() for f in assets for p in Path(f).parents if p.as_posix() != "."})
    entries, generated = [], []
    for rel in sorted(folders + assets):
        is_dir = rel in folders
        if rel in tracked_meta:
            meta = (PACKAGE_DIR / (rel + ".meta")).read_text()
        else:
            meta = generated_meta(rel, is_dir)
            generated.append(rel)
        entries.append((rel, None if is_dir else (PACKAGE_DIR / rel).read_bytes(), meta))
    return entries, generated


def meta_guid(meta):
    match = re.search(r"^guid: ([0-9a-f]{32})$", meta, re.M)
    if not match:
        raise ReleaseError("a .meta file has no 32-hex guid")
    return match.group(1)


# --- reproducible archives --------------------------------------------------

def add_bytes(tar, name, data, mtime, mode=0o644):
    info = tarfile.TarInfo(name)
    info.size, info.mtime, info.mode = len(data), mtime, mode
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    tar.addfile(info, io.BytesIO(data))


def add_dir(tar, name, mtime):
    info = tarfile.TarInfo(name)
    info.type, info.mtime, info.mode = tarfile.DIRTYPE, mtime, 0o755
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    tar.addfile(info)


def write_tgz(path, build, mtime):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        build(tar)
    with open(path, "wb") as out, gzip.GzipFile(filename="", fileobj=out, mode="wb", mtime=mtime) as gz:
        gz.write(raw.getvalue())


def upm_tarball(path, entries, mtime):
    def build(tar):
        for rel, data, meta in entries:
            if data is not None:
                add_bytes(tar, f"package/{rel}", data, mtime)
            add_bytes(tar, f"package/{rel}.meta", meta.encode(), mtime)
    write_tgz(path, build, mtime)


def unitypackage(path, entries, mtime):
    # Rooted at Packages/<name>/ rather than Assets/: importing it creates an
    # embedded package with the same identity, asmdef, and package.json as the
    # UPM install, instead of loose scripts under Assets/ that a later UPM
    # install would duplicate. The package root folder has no .meta in Unity,
    # so only its contents get entries.
    def build(tar):
        for rel, data, meta in sorted(entries, key=lambda e: meta_guid(e[2])):
            guid = meta_guid(meta)
            add_dir(tar, guid, mtime)
            if data is not None:
                add_bytes(tar, f"{guid}/asset", data, mtime)
            add_bytes(tar, f"{guid}/asset.meta", meta.encode(), mtime)
            add_bytes(tar, f"{guid}/pathname", f"Packages/{NAME}/{rel}".encode(), mtime)
    write_tgz(path, build, mtime)


def write_zip(path, files, mtime):
    stamp = time.gmtime(max(mtime, 315532800))[:6]  # zip cannot represent dates before 1980
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, source in sorted(files.items()):
            info = zipfile.ZipInfo(name, stamp)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, source.read_bytes())


# --- the engine-free core ---------------------------------------------------

def build_core(out, version, dotnet_sdk, mtime, tag):
    if not (dotnet_sdk / "Haiven.Sdk").is_dir():
        raise ReleaseError(f"{dotnet_sdk}/Haiven.Sdk not found; check out haiven-dev/haiven-sdk-dotnet there")
    # dotnet discovers global.json by walking upward from its process working
    # directory, not from the csproj. The release workflow runs this script
    # from the workspace parent and does not set working-directory: --out and
    # --dotnet-sdk are relative to that parent. A pin copied to ROOT is not on
    # that walk, so the copy alone does not pin publish. Publish with ROOT as
    # its working directory, and fail when the SDK resolved there is not the pin.
    pin_version = dotnet_pin(dotnet_sdk)
    pin_target = ROOT / "global.json"
    remove_pin = False
    pinned = bool(pin_version and dotnet_pin_installed(pin_version))
    if pinned:
        if not pin_target.exists():
            shutil.copyfile(dotnet_sdk / "global.json", pin_target)
            remove_pin = True
    elif pin_version and tag:
        raise ReleaseError(
            f".NET SDK {pin_version} from {dotnet_sdk / 'global.json'} is not installed; "
            "a tagged release must use that SDK")
    elif pin_version:
        print(f"note: .NET SDK {pin_version} is not installed; publishing with the default SDK",
              file=sys.stderr)
    try:
        if pinned:
            assert_pinned_sdk(pin_version)
            print(f"note: pinning dotnet publish to SDK {pin_version}", file=sys.stderr)
        return _publish_core(out, version, dotnet_sdk, mtime)
    finally:
        if remove_pin:
            pin_target.unlink(missing_ok=True)


def assert_pinned_sdk(pin_version):
    """Fail unless `dotnet`, started in ROOT, resolves pin_version."""
    selected = subprocess.run(
        ["dotnet", "--version"], cwd=ROOT, capture_output=True, text=True)
    chosen = selected.stdout.strip()
    if selected.returncode == 0 and chosen == pin_version:
        return
    if selected.returncode != 0:
        requested = next((
            line.strip() for line in selected.stderr.splitlines()
            if line.startswith("Requested SDK version:")
        ), "")
        extra = f"; {requested}" if requested else ""
        raise ReleaseError(
            f"dotnet in {ROOT} did not select pin {pin_version} "
            f"(exit {selected.returncode}){extra}")
    raise ReleaseError(f"dotnet in {ROOT} selected SDK {chosen}, not pin {pin_version}")


def _publish_core(out, version, dotnet_sdk, mtime):
    with tempfile.TemporaryDirectory(dir=out.parent) as scratch:
        # Absolute paths: cwd is ROOT, while the workflow's --out and
        # --dotnet-sdk are relative to the workspace parent.
        publish = (Path(scratch) / "publish").resolve()
        project = CORE_PROJECT.resolve()
        sdk_dir = dotnet_sdk.resolve()
        subprocess.run([
            "dotnet", "publish", str(project), "-c", "Release", "-o", str(publish),
            f"-p:HaivenSdkDotnetDir={sdk_dir}", f"-p:Version={version}",
            "-p:ContinuousIntegrationBuild=true", "-p:Deterministic=true",
        ], check=True, cwd=ROOT)
        dlls = {p.name: p for p in publish.glob("*.dll")}
        if "Haiven.Sdk.Core.dll" not in dlls:
            raise ReleaseError("dotnet publish produced no Haiven.Sdk.Core.dll")
        for name in ["Haiven.Sdk.Core.dll", "Haiven.Sdk.Core.pdb"]:
            shutil.copyfile(publish / name, out / name)
        # Same set ci/run.py installs into the host's Assets/Plugins/Core:
        # every managed DLL, nothing else. Unity supplies the platform itself.
        write_zip(out / f"haiven-sdk-core-{version}-netstandard2.1.zip", dlls, mtime)
        return sorted(dlls)


def sha256sums(out):
    lines = []
    for path in sorted(p for p in out.iterdir() if p.is_file() and p.name != "SHA256SUMS"):
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n")
    # write_bytes keeps the LF written above. write_text would emit CRLF on
    # Windows, and sha256sum -c would then look for names ending in CR.
    (out / "SHA256SUMS").write_bytes("".join(lines).encode())


def assert_same_assets(existing, built):
    """Fail when a published tag's assets are not byte-identical to this build."""
    def digests(directory):
        if not directory.is_dir():
            raise ReleaseError(f"{directory} is not a directory")
        found = {}
        for path in sorted(directory.iterdir()):
            if path.is_file():
                found[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if not found:
            raise ReleaseError(f"{directory} has no release assets")
        return found

    left, right = digests(existing), digests(built)
    if left.keys() != right.keys():
        missing = sorted(set(right) - set(left))
        extra = sorted(set(left) - set(right))
        raise ReleaseError(
            "existing release assets do not match this build "
            f"(missing {missing}, extra {extra}); publish a new version "
            "instead of replacing this tag")
    changed = [name for name in left if left[name] != right[name]]
    if changed:
        raise ReleaseError(
            "existing release assets differ for " + ", ".join(changed)
            + "; publish a new version instead of replacing this tag")
    print("existing release assets match this build; leaving them in place")


def assert_output_safe(out, dotnet_sdk):
    """--out is deleted before inputs are read. Refuse a path that would eat them."""
    if out == ROOT or out in ROOT.parents:
        raise ReleaseError(f"--out {out} is the repository or an ancestor of it")
    protected = [PACKAGE_DIR, ROOT / "core", ROOT / "ci", dotnet_sdk]
    for path in protected:
        if out == path or out in path.parents or path in out.parents:
            raise ReleaseError(f"--out {out} overlaps release input {path}")


def dotnet_pin(dotnet_sdk):
    pin = dotnet_sdk / "global.json"
    if not pin.is_file():
        return None
    try:
        version = json.loads(pin.read_text()).get("sdk", {}).get("version")
    except (OSError, json.JSONDecodeError):
        return None
    return version or None


def dotnet_pin_installed(version):
    listed = subprocess.run(["dotnet", "--list-sdks"], capture_output=True, text=True)
    if listed.returncode != 0:
        return False
    return any(line.split(" ", 1)[0] == version for line in listed.stdout.splitlines() if line.strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, type=Path,
                        help="directory for release assets (emptied first, unless --compare-to is set)")
    parser.add_argument("--tag", default="",
                        help="release tag; must equal v<package.json version>, and must not be v0.0.0")
    parser.add_argument("--dotnet-sdk", type=Path, default=ROOT.parent / "haiven-sdk-dotnet",
                        help="haiven-sdk-dotnet checkout providing Haiven.Sdk/*.cs")
    parser.add_argument("--notes", type=Path, help="also write release notes here (outside --out)")
    parser.add_argument("--compare-to", type=Path,
                        help="compare this existing asset directory to --out and exit without building or deleting")
    args = parser.parse_args()
    if args.compare_to:
        assert_same_assets(args.compare_to.resolve(), args.out.resolve())
        return

    version = resolve_version(args.tag)
    mtime = source_date_epoch()
    out = args.out.resolve()
    dotnet_sdk = args.dotnet_sdk.resolve()
    assert_output_safe(out, dotnet_sdk)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    entries, generated = package_entries()
    if generated:
        print(f"note: generated {len(generated)} .meta file(s) with path-derived GUIDs "
              f"(none are tracked): {', '.join(generated)}", file=sys.stderr)
    upm_tarball(out / f"{NAME}-{version}.tgz", entries, mtime)
    unitypackage(out / f"{NAME}-{version}.unitypackage", entries, mtime)
    core_dlls = build_core(out, version, dotnet_sdk, mtime, args.tag)
    sha256sums(out)

    if args.notes:
        dotnet_rev = subprocess.run(["git", "-C", str(dotnet_sdk), "rev-parse", "HEAD"],
                                    capture_output=True, text=True).stdout.strip() or "unknown"
        # Same LF rule as SHA256SUMS: write_text would use CRLF on Windows.
        args.notes.write_bytes((
            f"com.haiven.sdk {version}\n\n"
            f"- UPM tarball: `{NAME}-{version}.tgz` (install with `file:` path or a tarball URL)\n"
            f"- Unity package: `{NAME}-{version}.unitypackage` (imports as an embedded package under `Packages/{NAME}/`)\n"
            f"- Engine-free core: `Haiven.Sdk.Core.dll` (netstandard2.1), built from "
            f"haiven-dev/haiven-sdk-dotnet@{dotnet_rev}\n"
            f"- `haiven-sdk-core-{version}-netstandard2.1.zip`: the core plus its managed dependencies "
            f"({', '.join(core_dlls)}); place under `Assets/Plugins/` - the UPM package does not bundle them\n"
            f"- The Unity bridge assembly (`Haiven.Sdk`) ships as source in the package; Unity compiles it.\n\n"
            f"Verify downloads with `sha256sum -c SHA256SUMS`.\n").encode())

    for path in sorted(out.iterdir()):
        print(f"{path.stat().st_size:>10}  {path.name}")


if __name__ == "__main__":
    try:
        main()
    except (ReleaseError, subprocess.CalledProcessError, OSError) as error:
        sys.exit(f"release: {error}")
