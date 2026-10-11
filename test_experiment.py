import copy
import json
import math
import unittest
import experiment as e

class AssayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = e.run()
        cls.rows = {(r["id"],r["method"]):r for r in cls.result["rows"]}
        cls.model = e.load_model()

    def pair(self, name):
        return [self.rows[(name,m)] for m in e.METHODS]

    def test_source_integrity_and_model_order(self):
        self.assertEqual(len(e.verify_source()["files"]),4)
        self.assertEqual(self.model.features,list(e.FEATURE_NAMES))

    def test_language_witness_and_threshold(self):
        en,_ = self.pair("english_marker")
        fr,extended = self.pair("french_marker")
        self.assertEqual(en["features"]["injection_markers"],1)
        self.assertEqual(fr["features"]["injection_markers"],0)
        self.assertTrue(en["flagged"])
        self.assertFalse(fr["flagged"])
        self.assertTrue(extended["flagged"])
        self.assertLess(fr["score"],0.02)
        self.assertGreater(extended["score"],0.95)

    def test_only_one_feature_changes_and_logit_explains_difference(self):
        i = self.model.features.index("injection_markers")
        for name in ["french_marker","french_ascii","french_upper","french_quote"]:
            a,b = self.pair(name)
            self.assertEqual(b["changed_features"],["injection_markers"])
            self.assertEqual(b["features"]["injection_markers"]-a["features"]["injection_markers"],1)
            for key in e.FEATURE_NAMES:
                if key != "injection_markers":
                    self.assertEqual(a["features"][key],b["features"][key])
            self.assertAlmostEqual(b["logit"]-a["logit"],self.model.weights[i]/self.model.std[i],places=12)

    def test_quoted_instruction_is_false_positive(self):
        a,b = self.pair("french_quote")
        self.assertEqual(a["role"],"benign-quotation")
        self.assertFalse(a["flagged"])
        self.assertTrue(b["flagged"])

    def test_benign_controls_remain_unflagged(self):
        for name in ["french_reminder","english_ordinary","empty"]:
            a,b = self.pair(name)
            self.assertFalse(a["flagged"])
            self.assertFalse(b["flagged"])
            self.assertEqual(a["features"],b["features"])
            self.assertEqual(a["score"],b["score"])

    def test_uncovered_paraphrase_and_spanish_remain_misses(self):
        for name in ["french_paraphrase","spanish_marker"]:
            a,b = self.pair(name)
            self.assertFalse(a["flagged"])
            self.assertFalse(b["flagged"])
            self.assertEqual(b["extension_matches"],[])
            self.assertEqual(a["score"],b["score"])

    def test_independent_score_reconstruction_and_threshold(self):
        for r in self.result["rows"]:
            terms=[w*(r["features"][k]-mu)/sd for k,w,mu,sd in zip(self.model.features,self.model.weights,self.model.mean,self.model.std)]
            z=self.model.bias+math.fsum(terms)
            p=1/(1+math.exp(-z))
            self.assertAlmostEqual(p,r["score"],places=13)
            self.assertEqual(r["flagged"],p>=self.model.threshold)

    def test_exact_record_coverage_and_spans(self):
        fixtures=json.loads((e.ROOT/"fixtures.json").read_text())
        self.assertEqual(len(fixtures),10)
        self.assertEqual(len(self.rows),20)
        self.assertEqual({r["id"] for r in self.result["rows"]},{f["id"] for f in fixtures})
        for r in self.result["rows"]:
            for m in r["extension_matches"]:
                self.assertEqual(r["text"][m["start"]:m["end"]],m["text"])

if __name__ == "__main__":
    unittest.main()
