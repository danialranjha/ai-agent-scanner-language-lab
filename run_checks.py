"""Run focused tests and test functional faults in disposable copies."""
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def suite_result():
    stream=io.StringIO()
    with contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
        result=unittest.TextTestRunner(stream=stream).run(unittest.defaultTestLoader.discover(str(ROOT),pattern="test_experiment.py"))
    return {"tests":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),
            "failed_tests":[str(t) for t,_ in result.failures],"successful":result.wasSuccessful()}

if __name__=="__main__":
    if "--child" in sys.argv:
        print(json.dumps(suite_result(),sort_keys=True))
        raise SystemExit()
    baseline=suite_result()
    assert baseline["successful"],baseline
    faults={}
    original=(ROOT/"experiment.py").read_text()
    mutations={
        "omit_french_marker":("features[\"injection_markers\"] += len(matches)","features[\"injection_markers\"] += 0"),
        "flag_all_french":('"flagged": score >= model.threshold','"flagged": (fixture["language"] == "fr") or score >= model.threshold'),
    }
    for name,(old,new) in mutations.items():
        assert original.count(old)==1
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/"lab"
            shutil.copytree(ROOT,target,ignore=shutil.ignore_patterns(".git","__pycache__","*.pyc"))
            (target/"experiment.py").write_text(original.replace(old,new))
            proc=subprocess.run([sys.executable,"run_checks.py","--child"],cwd=target,text=True,capture_output=True,check=True)
            result=json.loads(proc.stdout)
            assert result["failures"]>0 and result["errors"]==0,(name,result)
            faults[name]=result
    data={"baseline":baseline,"functional_faults":faults,"runtime":sys.version.split()[0]}
    (ROOT/"artifacts/checks.json").write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print(json.dumps(data,indent=2))
