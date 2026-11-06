#!/usr/bin/env python3
"""Strict engine execution on an activated Linux editor with WebGL support."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
# This file lives in ci/ at the repository root. parents[2] was the monorepo
# root when the script lived at csharp/unity/ci/run.py.
SDK = HERE.parent
HOST = SDK / "host"
VERSION = "6000.0.52f1"
EXPECTED = {
    "EditMode": {"Haiven.Tests.ProtocolTests.LocalPackageLoads", "Haiven.Tests.ProtocolTests.RefusedReplyPreservesPresence", "Haiven.Tests.ProtocolTests.EventHasNoSuccessOrRequestId", "Haiven.Tests.ProtocolTests.HandoffDispatcherRunsOnUnityThread"},
    "PlayMode": {"Haiven.Tests.SocketTests.SocketRoundTripAndReconnect", "Haiven.Tests.HandoffTests.DeepLinkStoresTokenAndCompletesOnUnityThread"},
}


def verify_report(path, expected):
    root = ET.parse(path).getroot()
    cases = list(root.iter("test-case"))
    names = [case.get("fullname") for case in cases]
    if not cases or len(names) != len(set(names)) or not expected.issubset(set(names)):
        raise RuntimeError(f"missing or duplicate expected tests in {path}: {names}")
    if root.get("result") != "Passed" or any(case.get("result") != "Passed" for case in cases):
        raise RuntimeError(f"failed/skipped/inconclusive tests in {path}")


def main():
    results = Path(os.environ.get("HAIVEN_UNITY_RESULTS", SDK / "build/unity-results")).resolve()
    results.mkdir(parents=True, exist_ok=True)
    # Fresh result files; stale reports must never satisfy a later failed run.
    for name in ["EditMode.xml", "PlayMode.xml", "browser.json"]:
        (results / name).unlink(missing_ok=True)
    engine = shutil.which(os.environ.get("UNITY_EDITOR", "Unity"))
    if not engine:
        raise RuntimeError("activated Unity editor required; set UNITY_EDITOR")
    version = subprocess.check_output([engine, "-version"], text=True, timeout=30).strip()
    (results / "version.log").write_text(version + "\n")
    if version != VERSION:
        raise RuntimeError(f"expected Unity {VERSION}, got {version}")
    output = SDK / "build/unity-webgl"
    if output.exists(): shutil.rmtree(output)
    env = {**os.environ, "HAIVEN_WEBGL_OUTPUT": str(output), "HAIVEN_UNITY_RESULTS": str(results), "HAIVEN_TEST_SOCKET_URL": "ws://127.0.0.1:18765/socket"}

    def run(name, command, timeout=900):
        with (results / (name + ".log")).open("w") as log:
            subprocess.run(command, cwd=SDK, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=timeout)

    # The UPM package compiles Haiven.Sdk.Core from source. Publishing
    # Haiven.Sdk.Core.dll or its NuGet neighbors into Assets/Plugins duplicates
    # that assembly name, and Unity refuses to compile the project. Drop a
    # leftover publish from an older run so it cannot keep failing the host.
    stale_plugins = HOST / "Assets/Plugins/Core"
    if stale_plugins.exists(): shutil.rmtree(stale_plugins)
    with (results / "fixture.log").open("w") as fixture_log:
        fixture = subprocess.Popen(["node", str(HERE / "fixture.mjs")], env=env, stdout=fixture_log, stderr=subprocess.STDOUT)
        try:
            for attempt in range(50):
                if fixture.poll() is not None: raise RuntimeError("socket fixture failed to start")
                try:
                    with urllib.request.urlopen("http://127.0.0.1:18765/stats", timeout=1): break
                except OSError: time.sleep(.1)
            else: raise RuntimeError("socket fixture readiness timed out")
            common = [engine, "-batchmode", "-nographics", "-projectPath", str(HOST)]
            for mode, expected in EXPECTED.items():
                report = results / (mode + ".xml")
                run(mode, common + ["-runTests", "-testPlatform", mode, "-testFilter", "Haiven.Tests", "-testResults", str(report), "-logFile", str(results / (mode + "-editor.log"))])
                verify_report(report, expected)
            run("build", common + ["-quit", "-buildTarget", "WebGL", "-executeMethod", "HaivenBuild.WebGL", "-logFile", str(results / "build-editor.log")], timeout=1800)
            run("browser", ["node", str(HERE / "browser.mjs")], timeout=180)
        finally:
            fixture.terminate()
            try: fixture.wait(timeout=5)
            except subprocess.TimeoutExpired: fixture.kill(); fixture.wait()


if __name__ == "__main__":
    try: main()
    except (RuntimeError, OSError, subprocess.SubprocessError, ET.ParseError) as error:
        sys.exit(str(error))
