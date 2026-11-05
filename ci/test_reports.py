import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("unity_runner", Path(__file__).with_name("run.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

class ReportTests(unittest.TestCase):
    def test_reports_require_expected_passing_cases(self):
        cases = [
            ('<test-run result="Passed"><test-case fullname="expected" result="Passed"/></test-run>', True),
            ('<test-run result="Passed"/>', False),
            ('<test-run result="Passed"><test-case fullname="other" result="Passed"/></test-run>', False),
            ('<test-run result="Passed"><test-case fullname="expected" result="Skipped"/></test-run>', False),
            ('<test-run result="Failed"><test-case fullname="expected" result="Passed"/></test-run>', False),
            ('<test-run result="Passed"><test-case fullname="expected" result="Passed"/><test-case fullname="expected" result="Passed"/></test-run>', False),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.xml"
            for xml, valid in cases:
                with self.subTest(xml=xml):
                    path.write_text(xml)
                    if valid: runner.verify_report(path, {"expected"})
                    else:
                        with self.assertRaises(RuntimeError): runner.verify_report(path, {"expected"})

    def test_editor_pin_is_unity_6_0(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(runner.SDK, root)
        self.assertEqual(runner.HOST, root / "host")
        self.assertEqual(runner.VERSION, "6000.0.52f1")
        manifest = json.loads((root / "com.haiven.sdk/package.json").read_text())
        self.assertEqual(manifest["unity"], "6000.0")
        version = (root / "host/ProjectSettings/ProjectVersion.txt").read_text()
        self.assertEqual(
            version,
            "m_EditorVersion: 6000.0.52f1\n"
            "m_EditorVersionWithRevision: 6000.0.52f1 (9e4086222921)\n",
        )
        build = (root / "host/Assets/Editor/HaivenBuild.cs").read_text()
        self.assertEqual(build.count(runner.VERSION), 2)
        browser = (root / "ci/browser.mjs").read_text()
        self.assertIn(f'unity:"{runner.VERSION}"', browser)

if __name__ == "__main__": unittest.main()
