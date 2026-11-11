"""Exercise the shared launcher without contacting Slurm or running training."""
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HERE = Path(__file__).resolve().parent
launch = load_module('launch', HERE.parent/'launch.py')
restore = load_module('restore_workflow', HERE/'restore_workflow.py')


class LaunchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.workspace = json.loads((launch.EXPERIMENTS/'workspace.example.json').read_text())
        self.workspace['output_root'] = str(self.root/'outputs')
        self.workspace_path = self.root/'workspace.json'
        self.workspace_path.write_text(json.dumps(self.workspace))
        self.entry, self.config, self.tasks = launch.load('pbmc_gcn_comparison')

    def test_dry_run_is_read_only_and_evaluation_waits(self):
        with patch.object(launch.subprocess,'check_output') as scheduler:
            train, evaluate = launch.submit_plan(
                self.entry,self.config,self.tasks,self.workspace_path,self.workspace,['train','evaluate'])
        scheduler.assert_not_called()
        self.assertFalse(Path(self.workspace['output_root']).exists())
        self.assertIn('--dependency=afterok:<TRAIN_JOB_ID>',evaluate)
        self.assertIn('--array=0-48%6',train)
        self.assertIn('--array=1-48%6',evaluate)
        self.assertIn('--gpus-per-node=h100:1',train)
        self.assertFalse(any('--gpus-' in part for part in evaluate))

    def test_dispatch_records_jobs_and_refuses_duplicate(self):
        with patch.object(launch,'verify_sources'),patch.object(launch,'check_inputs'),patch.object(
                launch.subprocess,'check_output',side_effect=['123;fir\n','124;fir\n']) as scheduler:
            launch.submit_plan(self.entry,self.config,self.tasks,self.workspace_path,self.workspace,['train','evaluate'],submit=True)
            self.assertIn('--dependency=afterok:123',scheduler.call_args_list[1].args[0])
            with self.assertRaisesRegex(ValueError,'Existing submission reservation'):
                launch.submit_plan(self.entry,self.config,self.tasks,self.workspace_path,self.workspace,['train'],submit=True)
            self.assertEqual(scheduler.call_count,2)
        record = json.loads((Path(self.workspace['output_root'])/self.entry['id']/'submission.json').read_text())
        self.assertEqual(record['status'],'submitted')
        self.assertEqual([job['job_id'] for job in record['jobs']],['123','124'])

    def test_ambiguous_scheduler_reply_preserves_reservation(self):
        with patch.object(launch,'verify_sources'),patch.object(launch,'check_inputs'),patch.object(
                launch.subprocess,'check_output',side_effect=['123\n','']) as scheduler:
            with self.assertRaisesRegex(ValueError,'Unrecognized sbatch response'):
                launch.submit_plan(self.entry,self.config,self.tasks,self.workspace_path,self.workspace,['train','evaluate'],submit=True)
            with self.assertRaisesRegex(ValueError,'Existing submission reservation'):
                launch.submit_plan(self.entry,self.config,self.tasks,self.workspace_path,self.workspace,['train'],submit=True)
            self.assertEqual(scheduler.call_count,2)
        record = json.loads((Path(self.workspace['output_root'])/self.entry['id']/'submission.json').read_text())
        self.assertEqual(record['status'],'needs_manual_review')
        self.assertEqual(record['jobs'][0]['job_id'],'123')
        self.assertIn('--dependency=afterok:123',record['pending_command'])

    def test_workspace_hash_changes_with_configuration(self):
        expected = launch.design_digest(self.entry,self.workspace_path)
        self.workspace['partitions']['gpu'] = 'another_partition'
        self.workspace_path.write_text(json.dumps(self.workspace))
        self.assertNotEqual(expected,launch.design_digest(self.entry,self.workspace_path))

    def test_protected_output_and_symlink_are_refused(self):
        with self.assertRaisesRegex(ValueError,'protected'):
            launch.safe_workspace(dict(self.workspace,output_root=str(launch.REPO/'outputs')))
        output = Path(self.workspace['output_root'])
        output.mkdir()
        (output/self.entry['id']).symlink_to(launch.REPO,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'without symlinks'):
            launch.submit_plan(self.entry,self.config,self.tasks,self.workspace_path,self.workspace,['train'])

    def test_gcn_dimensions_preserve_gat_runner_gcn_mode(self):
        entry, config, tasks = launch.load('pbmc_dimensions')
        plan = launch.task_plan(entry,config,tasks[0],self.workspace)
        args = plan['command']
        self.assertEqual(plan['implementation'],self.workspace['implementations']['gat'])
        self.assertEqual(args[args.index('--graph-encoder')+1],'gcn')
        self.assertEqual(args[args.index('--dim')+1],'16')

    def test_pbmc_dimensions_cover_the_complete_matched_design(self):
        entry, config, tasks = launch.load('pbmc_dimensions')
        self.assertEqual([int(task['task_id']) for task in tasks],list(range(30)))
        identities = []
        reused = []
        for task in tasks:
            subset = re.fullmatch(r'subsample_size:(\d+)-subsample_seed:(\d+)',
                                  Path(task['rna_path']).parent.name)
            self.assertIsNotNone(subset)
            size, subset_seed = map(int,subset.groups())
            identity = (task['architecture'],size,int(task['dim']),subset_seed,int(task['model_seed']))
            identities.append(identity)
            if task['reuse_source']:
                reused.append(identity)
        expected = {(arch,size,dim,0,0) for arch in ('gcn','gat','gated')
                    for size in (2000,8000) for dim in (16,32,50,64,100)}
        self.assertEqual(len(identities),len(set(identities)))
        self.assertEqual(set(identities),expected)
        self.assertEqual(set(reused),{(arch,size,50,0,0) for arch in ('gcn','gat','gated')
                                     for size in (2000,8000)})
        self.assertEqual(len(reused),6)
        self.assertTrue(config['reuse_metrics'])

    def test_restored_dimension_references_return_before_training(self):
        entry, config, tasks = launch.load('pbmc_dimensions')
        self.assertEqual([task['architecture'] for task in tasks[27:]],['gcn','gat','gated'])
        for task in tasks[27:]:
            with self.subTest(architecture=task['architecture']):
                self.assertTrue(task['reuse_source'])
                source = Path(launch.resolve(task['reuse_source'],self.workspace)).resolve()
                plan = launch.task_plan(entry,config,task,self.workspace)
                self.assertTrue(plan['reuse_source'])
                self.assertEqual(Path(plan['run_directory']),source)
                # Exercise only the guarded read-only return. Any attempt to
                # plan or start a scientific process fails before it can run.
                with patch.dict(os.environ,{'SLURM_JOB_ID':'unit-test'}),patch.object(
                        launch,'verify_sources'),patch.object(launch,'check_inputs'),patch.object(
                        launch,'require_training_files') as artifacts,patch.object(
                        launch,'task_plan',side_effect=AssertionError('Reuse must not start training')),patch.object(
                        launch.subprocess,'run',side_effect=AssertionError('No subprocess allowed')),patch.object(
                        launch,'call',side_effect=AssertionError('No scientific command allowed')),patch('builtins.print'):
                    launch.execute_task(entry,config,task,self.workspace,'train')
                artifacts.assert_called_once_with(source)
        self.assertFalse(Path(self.workspace['output_root']).exists())

    def test_blocked_evaluation_does_not_contact_scheduler(self):
        entry, config, tasks = launch.load('pbmc_gat_tuning')
        with patch.object(launch.subprocess,'check_output') as scheduler:
            with self.assertRaisesRegex(ValueError,'feature references'):
                launch.submit_plan(entry,config,tasks,self.workspace_path,self.workspace,['train','evaluate'],submit=True)
        scheduler.assert_not_called()
        self.assertFalse(Path(self.workspace['output_root']).exists())

    def test_restore_workflow_refuses_existing_destination(self):
        destination = self.root/'snapshot'
        snapshot = 'evaluation/gat_tuning_10x/screen_v2/configs/lr_0p001/workflow'
        count = restore.restore(snapshot,destination)
        self.assertEqual(count,40)
        self.assertIn('--lr 0.001',(destination/'rules/methods.smk').read_text())
        with self.assertRaises(FileExistsError):
            restore.restore(snapshot,destination)


if __name__ == '__main__':
    unittest.main()
