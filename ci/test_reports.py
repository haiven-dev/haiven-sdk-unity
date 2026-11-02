import importlib.util
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

if __name__ == "__main__": unittest.main()
