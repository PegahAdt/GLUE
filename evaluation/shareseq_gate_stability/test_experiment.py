"""Regression checks using metadata/embedding fixtures, never training."""

import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import h5py
import numpy as np
import pandas as pd
import yaml

import experiment
from analyze import pairwise_counts, seed_statistics


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="shareseq_validator_")
        self.output = Path(self.temporary.name)
        self.row = next(row for row in experiment.read_rows(experiment.FULL.MAN) if row["architecture"] == "gated" and row["latent_dim"] == "16").copy()
        self.row.update(output_directory=str(self.output), latent_dim="1", model_seed="2", gate_init="0.25")
        self.ids = Path(self.row["cell_manifest_path"]).read_text().splitlines()
        self.arguments = dict(experiment.FULL.FIXED, dim=1, random_seed=2, gate_init=0.25, lam_keep=0,
                              graph_encoder="gated", prior=self.row["graph_path"])
        (self.output / "final.dill").write_bytes(b"Validator file-presence fixture; not a trained model")
        for modality in ("rna", "atac"):
            with h5py.File(self.output / f"{modality}.h5ad", "w") as handle:
                obs = handle.create_group("obs")
                obs.attrs["_index"] = "_index"
                obs.create_dataset("_index", data=np.asarray(self.ids, dtype=object), dtype=h5py.string_dtype())
            pd.DataFrame(np.zeros((len(self.ids), 1)), index=self.ids).to_csv(self.output / f"{modality}_latent.csv", header=False)
        pd.DataFrame([[0.1]], index=["feature"]).to_csv(self.output / "feature_latent.csv", header=False)
        self.stamp()

    def tearDown(self):
        self.temporary.cleanup()

    def stamp(self):
        (self.output / "requested_configuration.json").write_text(json.dumps(self.row))
        (self.output / "run_info.yaml").write_text(yaml.safe_dump(dict(args=self.arguments, time=1.0, cmd=str(experiment.TRAINING))))

    def test_accepts_nondefault_seed_and_gate(self):
        self.assertEqual(experiment.FULL.validate(self.row), 1.0)

    def test_accepts_legacy_defaults(self):
        self.row.update(model_seed="0", gate_init="0.95")
        self.arguments.update(random_seed=0, gate_init=0.95)
        self.stamp()
        self.assertEqual(experiment.FULL.validate(self.row), 1.0)

    def test_rejects_seed_mismatch(self):
        self.arguments["random_seed"] = 0
        self.stamp()
        with self.assertRaises(AssertionError):
            experiment.FULL.validate(self.row)

    def test_rejects_gate_mismatch(self):
        self.arguments["gate_init"] = 0.95
        self.stamp()
        with self.assertRaises(AssertionError):
            experiment.FULL.validate(self.row)

    def test_rejects_changed_fixed_hyperparameter(self):
        self.arguments["lam_align"] = 0.02
        self.stamp()
        with self.assertRaises(AssertionError):
            experiment.FULL.validate(self.row)

    def test_rejects_missing_checkpoint(self):
        (self.output / "final.dill").unlink()
        with self.assertRaises(AssertionError):
            experiment.FULL.validate(self.row)

    def test_rejects_nonfinite_embedding(self):
        pd.DataFrame(np.full((len(self.ids), 1), np.nan), index=self.ids).to_csv(self.output / "rna_latent.csv", header=False)
        with self.assertRaises(AssertionError):
            experiment.FULL.validate(self.row)

    def test_rejects_changed_cell_order(self):
        pd.DataFrame(np.zeros((len(self.ids), 1)), index=self.ids[::-1]).to_csv(self.output / "rna_latent.csv", header=False)
        with self.assertRaises(AssertionError):
            experiment.FULL.validate(self.row)

    def test_rejects_changed_graph_checksum(self):
        self.row["graph_checksum"] = "incorrect"
        self.stamp()
        with self.assertRaises(AssertionError):
            experiment.FULL.validate(self.row)


class SweepAndAnalysisTests(unittest.TestCase):
    def test_fresh_training_process_imports(self):
        experiment.environment_check()
        probe = (
            "import torch; import scglue; import inspect, json, os; "
            "print(json.dumps({'scglue': scglue.__file__, "
            "'model_source': inspect.getfile(scglue.models.SCGLUEModel), "
            "'mkl_threading_layer': os.environ.get('MKL_THREADING_LAYER'), "
            "'model_parameters': list(inspect.signature(scglue.models.SCGLUEModel).parameters)}))"
        )
        result = subprocess.run([sys.executable, "-u", "-c", probe], cwd=experiment.SHARED,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(Path(report["scglue"]).resolve(), experiment.REPO / "scglue/__init__.py")
        self.assertEqual(Path(report["model_source"]).resolve(), experiment.REPO / "scglue/models/scglue.py")
        self.assertEqual(report["mkl_threading_layer"], "GNU")
        self.assertIn("gate_init", report["model_parameters"])
        self.assertIn("graph_encoder", report["model_parameters"])
        print("Fresh training-process import verified: " + json.dumps(report), flush=True)

    def test_manifest_and_duplicate_rejection(self):
        rows = experiment.read_rows()
        experiment.verify_manifest(rows)
        rows[-1] = rows[0].copy()
        with self.assertRaises(ValueError):
            experiment.verify_manifest(rows)

    def test_seed_statistics_known_sets(self):
        masks = np.array([[True, True, False, False], [False, True, True, False], [False, True, False, True]])
        result = seed_statistics(masks)
        self.assertAlmostEqual(result["mean_pairwise_jaccard"], 1 / 3)
        self.assertEqual(result["sd_pairwise_jaccard"], 0)
        self.assertEqual(result["three_seed_intersection_size"], 1)
        self.assertEqual(result["three_seed_union_size"], 4)
        self.assertEqual(result["n_edges_at_least_2_of_3"], 1)
        self.assertEqual(result["pct_edges_all_3_of_3"], 25)

    def test_empty_and_disjoint_sets(self):
        empty = seed_statistics(np.zeros((3, 4), dtype=bool))
        self.assertEqual(empty["mean_pairwise_jaccard"], 1)
        self.assertEqual(empty["empty_seed_sets"], 3)
        self.assertEqual(empty["three_seed_union_size"], 0)
        self.assertEqual(pairwise_counts(np.eye(2, dtype=bool))[0]["jaccard"], 0)

    def test_packed_counts_match_sets(self):
        masks = np.random.RandomState(7).rand(6, 37) < 0.4
        for pair, (first, second) in zip(pairwise_counts(masks), itertools.combinations(range(6), 2)):
            first_set = set(np.flatnonzero(masks[first]))
            second_set = set(np.flatnonzero(masks[second]))
            self.assertEqual(pair["intersection_size"], len(first_set & second_set))
            self.assertEqual(pair["union_size"], len(first_set | second_set))


if __name__ == "__main__":
    unittest.main()
