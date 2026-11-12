"""Cross-architecture integration invariants; standard library, no scientific imports."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('release_validator',ROOT/'scripts/validate_release.py')
validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.profiles=json.loads((ROOT/'provenance/implementation_versions.json').read_text())

    def test_all_original_source_profiles_match(self):
        for name,profile in self.profiles.items():
            with self.subTest(profile=name):self.assertEqual(validator.profile_failures(ROOT,profile),[])

    def test_source_guard_detects_runner_substitution(self):
        # A wrong architecture can share the package version label. Digest identity,
        # rather than that label, must reject an accidental runner replacement.
        path='evaluation/workflow/scripts/run_GLUE.py'
        profile=dict(root='.',files={path:self.profiles['gat']['files'][path]})
        with tempfile.TemporaryDirectory() as folder:
            dest=Path(folder)/path;dest.parent.mkdir(parents=True)
            dest.write_bytes((ROOT/path).read_bytes())
            self.assertEqual(validator.profile_failures(Path(folder),profile),[path])

    def test_gated_pbmc_runner_is_distinct_and_model_alias_explicit(self):
        p=ROOT/'implementations/gated_pbmc/scglue'
        self.assertTrue(p.is_symlink())
        self.assertEqual(p.resolve(),ROOT/'implementations/gated/scglue')
        runner='evaluation/workflow/scripts/run_GLUE.py'
        self.assertNotEqual(self.profiles['gated']['files'][runner],self.profiles['gated_pbmc']['files'][runner])
        helper=ROOT/'implementations/gated_pbmc/evaluation/workflow/scripts/graph_perturbation.py'
        self.assertTrue(helper.is_symlink())
        self.assertEqual(helper.resolve(),ROOT/'evaluation/workflow/scripts/graph_perturbation.py')

    def test_three_canonical_fingerprints_match_the_selected_sources(self):
        fingerprints=json.loads((ROOT/'experiments/common/architecture_sources.json').read_text())
        for name,definition in fingerprints.items():
            for path,expected in definition['files'].items():
                self.assertEqual(self.profiles[name]['files'][path],expected,(name,path))

    def test_existing_launcher_accepts_unified_source_bindings(self):
        spec=importlib.util.spec_from_file_location('canonical_launch',ROOT/'experiments/launch.py')
        launch=importlib.util.module_from_spec(spec);spec.loader.exec_module(launch)
        workspace={'implementations':{name:str(ROOT/self.profiles[name]['root']) for name in ['gcn','gat','gated']}}
        for name in ['gcn','gat','gated']:
            launch.verify_sources({'implementation':name},workspace)

    def test_catalog_and_manuscript_uncertainty_are_explicit(self):
        rows=json.loads((ROOT/'provenance/experiment_map.json').read_text())
        catalog=json.loads((ROOT/'experiments/catalog.json').read_text())
        self.assertEqual(len(rows),35)
        self.assertEqual(len({x['id'] for x in rows}),35)
        self.assertTrue({x['id'] for x in catalog}<={x['id'] for x in rows})
        self.assertTrue(all(x['thesis_section']=='Manuscript verification required' for x in rows))
        unknown=next(x for x in rows if x['id']=='share_graph_retention_unlocated')
        self.assertFalse(unknown['train'])


if __name__=='__main__':
    unittest.main()
