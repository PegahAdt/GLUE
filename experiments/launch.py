#!/usr/bin/env python3
"""Canonical experiment planner and guarded Slurm dispatcher. Default: read-only plan."""
import argparse
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
EXPERIMENTS = REPO/'experiments'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(8*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def within(path, parent):
    path, parent = Path(path).resolve(), Path(parent).resolve()
    return path == parent or parent in path.parents


def load(experiment):
    catalog = json.loads((EXPERIMENTS/'catalog.json').read_text())
    entry = next((x for x in catalog if x['id'] == experiment), None)
    if entry is None:
        raise ValueError('Unknown experiment; use --list')
    directory = EXPERIMENTS/entry['directory']
    config = json.loads((directory/'config.json').read_text())
    manifest = directory/'manifest.csv'
    tasks = []
    if manifest.exists():
        with manifest.open(newline='') as handle:
            tasks = list(csv.DictReader(handle))
    if tasks and [int(x['task_id']) for x in tasks] != list(range(len(tasks))):
        raise ValueError('Array indices must be contiguous and match manifest row order')
    return entry, config, tasks


def resolve(value, workspace):
    """Longest explicit prefix wins; paths are data, never evaluated as shell text."""
    for old, new in sorted(workspace.get('path_bindings', {}).items(), key=lambda x: -len(x[0])):
        if value == old or value.startswith(old.rstrip('/')+'/'):
            target = REPO/new[5:] if new.startswith('repo:') else Path(new)
            return str(target/value[len(old):].lstrip('/'))
    return value


def implementation(task, workspace):
    return Path(workspace['implementations'][task['implementation']]).resolve()


def run_directory(entry, task, workspace):
    if task.get('reuse_source'):
        return Path(resolve(task['reuse_source'], workspace)).resolve()
    return Path(workspace['output_root']).resolve()/entry['id']/'runs'/task['task_id']


def runner_arguments(config, task, output, workspace):
    data = {key:resolve(task[key], workspace) for key in ('rna_path','atac_path','graph_path')}
    if task.get('cell_manifest_path'):
        data['rna_path'], data['atac_path'] = str(output/'rna.h5ad'), str(output/'atac.h5ad')
    args = ['--input-rna',data['rna_path'],'--input-atac',data['atac_path'],'--prior',data['graph_path']]
    settings = dict(config['training'])
    for key in ('dim','gate_init','lam_keep','gat_negative_slope','lr','lam_graph','lam_align','model_seed'):
        value = task.get(key)
        if value not in (None,''):
            settings['random_seed' if key == 'model_seed' else key] = value
    settings['dim'] = task['dim']
    if task['implementation'] != 'gcn':
        settings['graph_encoder'] = task['architecture']
    if task['architecture'] != 'gated':
        settings.pop('gate_init',None);settings.pop('lam_keep',None)
    if task['architecture'] != 'gat':
        settings.pop('gat_negative_slope',None)
    for key,value in settings.items():
        if value is False or value is None:
            continue
        args.append('--'+key.replace('_','-'))
        if value is not True:
            args.append(str(value))
    args += ['--train-dir',str(output)]
    for name in ('rna','atac','feature'):
        args += ['--output-'+name,str(output/(name+'_latent.csv'))]
    return args+['--run-info',str(output/'run_info.yaml')]


def task_plan(entry, config, task, workspace):
    output = run_directory(entry,task,workspace)
    impl = implementation(task,workspace)
    python = workspace['python']
    script = impl/'evaluation/workflow/scripts/run_GLUE.py'
    arguments = runner_arguments(config,task,output,workspace)
    if config.get('resource_wrapper'):
        script = REPO/'evaluation/shareseq_ma2020/scripts/full_dimension_resource_run.py'
    command = [python,'-B','-u',str(script)]+arguments
    return dict(task_id=int(task['task_id']),architecture=task['architecture'],implementation=str(impl),
                run_directory=str(output),reuse_source=bool(task.get('reuse_source')),command=command,
                input_paths={k:resolve(task[k],workspace) for k in ('rna_path','atac_path','graph_path','cell_manifest_path') if task.get(k)},
                source_row=task.get('source_row',''))


def verify_sources(task, workspace):
    fingerprints = json.loads((EXPERIMENTS/'common/architecture_sources.json').read_text())
    root = implementation(task,workspace)
    for relative, expected in fingerprints[task['implementation']]['files'].items():
        path=root/relative
        if not path.is_file() or digest(path) != expected:
            raise ValueError('Architecture/runner source mismatch: '+str(path))


def environment(impl, workspace):
    env = os.environ.copy()
    env.pop('PYTHONHOME',None);env.pop('DIMENSION_SMOKE',None)
    env.update(PYTHONPATH=str(impl),PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',MKL_THREADING_LAYER='GNU')
    library = str(Path(workspace['python']).resolve().parents[1]/'lib')
    env['LD_LIBRARY_PATH'] = library+os.pathsep+env.get('LD_LIBRARY_PATH','')
    threads = env.get('SLURM_CPUS_PER_TASK','1')
    for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMBA_NUM_THREADS'):
        env[key]=threads
    return env


def safe_workspace(workspace):
    output = Path(workspace['output_root']).resolve()
    protected = [REPO]+[Path(x).resolve() for x in workspace['implementations'].values()]
    protected += [Path(x).resolve() for x in workspace.get('protected_roots',[])]
    # Firm protection against accidental writes into any existing research worktree.
    protected += [Path('/project/6001426/paa40/GlUE_Exp'),Path('/project/6001426/paa40/GLUE/GLUE')]
    for root in protected:
        if within(output,root) or within(root,output):
            raise ValueError('Output root overlaps a protected code/research root: '+str(root))
    for source in workspace.get('path_bindings',{}).values():
        if source.startswith('repo:'):
            source = REPO/source[5:]
        if within(output,source) or within(source,output):
            raise ValueError('Output root overlaps an input binding: '+str(source))
    return output


def checked_output(root, path):
    if path.resolve() != path or not within(path, root):
        raise ValueError('Output must stay in the fresh output root without symlinks: '+str(path))
    return path


def check_inputs(task, workspace, checked=None):
    for key in ('rna_path','atac_path','graph_path','cell_manifest_path'):
        if not task.get(key):continue
        path = Path(resolve(task[key],workspace))
        expected=task.get(key+'_sha256')
        identity=(path,expected)
        if checked is not None and identity in checked:
            continue
        if not path.is_file() or not path.stat().st_size:
            raise ValueError('Missing input '+key+': '+str(path))
        if expected and digest(path)!=expected:
            raise ValueError('Input checksum mismatch: '+str(path))
        if checked is not None:
            checked.add(identity)


def call(command, cwd, env, logfile):
    with Path(logfile).open('x') as log:
        subprocess.run(command,cwd=str(cwd),env=env,stdout=log,stderr=subprocess.STDOUT,check=True)


def execute_task(entry, config, task, workspace, phase):
    if not os.environ.get('SLURM_JOB_ID'):
        raise ValueError('Execution requires a Slurm allocation')
    root=safe_workspace(workspace)
    verify_sources(task,workspace);check_inputs(task,workspace)
    if phase=='train' and task.get('reuse_source'):
        require_training_files(run_directory(entry,task,workspace))
        print('REUSE (read-only): '+resolve(task['reuse_source'],workspace))
        return
    plan=task_plan(entry,config,task,workspace)
    impl=Path(plan['implementation']);env=environment(impl,workspace)
    output=Path(plan['run_directory'])
    probe=[workspace['python'],'-B','-c','import pathlib,scglue,sys; assert pathlib.Path(scglue.__file__).resolve()==pathlib.Path(sys.argv[1]).resolve()',str(impl/'scglue/__init__.py')]
    subprocess.run(probe,cwd=str(impl),env=env,check=True)
    if phase=='train':
        checked_output(root,output)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.mkdir()  # Existing partial or complete runs are never overwritten.
        (output/'requested_task.json').write_text(json.dumps(dict(task=task,configuration=config,plan=plan),indent=2)+'\n')
        if task.get('cell_manifest_path'):
            command=[workspace['python'],'-B',str(REPO/'evaluation/shareseq_ma2020/scripts/materialize_run_inputs.py'),str(output),
                     resolve(task['rna_path'],workspace),resolve(task['atac_path'],workspace),resolve(task['cell_manifest_path'],workspace)]
            call(command,impl,env,output/'materialize.log')
        call(plan['command'],impl,env,output/'run_GLUE.log')
        require_training_files(output)
        if task['architecture']=='gated' and not (output/'gate_diagnostics.yaml').is_file():
            raise ValueError('Missing GATED diagnostics')
        (output/'TRAINING_COMPLETE').write_text('Training artifacts present; scientific evaluation is a separate phase.\n')
    else:
        if config.get('evaluation_blocker'):raise ValueError(config['evaluation_blocker'])
        evaluate(entry,config,task,workspace,output)


def require_training_files(directory):
    for name in ('final.dill','run_info.yaml','rna_latent.csv','atac_latent.csv','feature_latent.csv'):
        path = directory/name
        if not path.is_file() or not path.stat().st_size:
            raise ValueError('Missing training artifact: '+str(path))


def evaluate(entry,config,task,workspace,output):
    """Use unchanged metric scripts; isolate all generated representations and metrics."""
    require_training_files(output)
    root = safe_workspace(workspace)
    destination=checked_output(root,root/entry['id']/'metrics'/task['task_id'])
    verify_sources({'implementation':'gcn'},workspace)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.mkdir()
    if task.get('reuse_source') and config.get('reuse_metrics'):
        (destination/'metrics.yaml').write_bytes((output/'metrics.yaml').read_bytes())
        (destination/'EVALUATED').write_text('Reused the historical 50D metric YAML byte for byte.\n')
        return
    impl=Path(workspace['implementations']['gcn']).resolve();env=environment(impl,workspace)
    base=impl/'evaluation/workflow/scripts';python=workspace['python']
    if task.get('cell_manifest_path'):
        manifest = resolve(task['cell_manifest_path'],workspace)
        references = json.loads((EXPERIMENTS/'shareseq/unirep_references.json').read_text())
        recorded = references[task['cell_manifest_path_sha256']]
        reps = [resolve(recorded[name]['path'],workspace) for name in ('rna','atac')]
        for path, name in zip(reps,('rna','atac')):
            if digest(path) != recorded[name]['sha256']:
                raise ValueError('SHARE representation checksum mismatch: '+path)
        check = EXPERIMENTS/'common/validate_share_metrics.py'
        call([python,'-B',str(check),manifest,str(output),task['dim'],*reps],impl,env,destination/'validate_inputs.log')
    elif config.get('evaluation_representations')=='prepared':
        reps=[resolve(task[key],workspace) for key in ('rna_path','atac_path')]
    else:
        reps=[str(Path(resolve(task['rna_path'],workspace)).parent/(m+'_unirep.h5ad')) for m in ('rna','atac')]
    for path in reps:
        if not Path(path).is_file():raise ValueError('Missing canonical representation: '+path)
    integration=destination/'cell_integration.yaml'
    call([python,'-B',str(base/'cell_integration.py'),'-d']+reps+['-l',str(output/'rna_latent.csv'),str(output/'atac_latent.csv'),
         '--cell-type','cell_type','--domain','domain','--paired','-o',str(integration)],impl,env,destination/'cell_integration.log')
    files=[str(output/'run_info.yaml'),str(integration)]
    if task.get('feature_reference'):
        reference=resolve(task['feature_reference'],workspace)
        if reference.startswith('task:'):
            reference=str(Path(workspace['output_root']).resolve()/entry['id']/'runs'/reference[5:]/'feature_latent.csv')
        consistency=destination/'feature_consistency.yaml'
        call([python,'-B',str(base/'feature_consistency.py'),'-q',str(output/'feature_latent.csv'),'-r',reference,'-o',str(consistency)],impl,env,destination/'feature_consistency.log')
        files.append(str(consistency))
    if not task.get('cell_manifest_path'):
        call([python,'-B',str(base/'combine_metrics.py'),'-i']+files+['-o',str(destination/'metrics.yaml')],impl,env,destination/'combine_metrics.log')
    else:
        call([python,'-B',str(EXPERIMENTS/'common/validate_share_metrics.py'),'--metrics',str(integration)],impl,env,destination/'validate_metrics.log')
    (destination/'EVALUATED').write_text('Canonical metric entrypoints completed.\n')


def submit_plan(entry,config,tasks,workspace_path,workspace,phases,submit=False):
    output_root=safe_workspace(workspace)
    root=checked_output(output_root,output_root/entry['id'])
    commands=[]
    count=len(tasks)
    if not count:raise ValueError('No executed design to dispatch')
    for phase in phases:
        resource=config['resources'][phase]
        first = 1 if phase=='evaluate' and config.get('reference_task_zero') else 0
        command=['sbatch','--parsable','--job-name=glue_'+entry['id']+'_'+phase,
                 '--cpus-per-task='+str(resource['cpus']),'--mem='+resource['memory'],'--time='+resource['time'],
                 '--partition='+workspace['partitions']['gpu' if phase=='train' else 'cpu'],
                 '--array={}-{}%{}'.format(first,count-1,resource['concurrency']),
                 '--output='+str(root/'logs'/(phase+'_%A_%a.out')),'--error='+str(root/'logs'/(phase+'_%A_%a.err'))]
        if phase=='train':command+=['--gpus-per-node='+resource['gpu']]
        if phase=='evaluate' and 'train' in phases:command+=['--dependency=afterok:<TRAIN_JOB_ID>']
        payload=[workspace['python'],'-B',str(Path(__file__).resolve()),entry['id'],'--workspace',str(Path(workspace_path).resolve()),'--execute-task',phase]
        payload+=['--design-digest',design_digest(entry,workspace_path)]
        command+=['--wrap',shlex.join(payload)]
        commands.append(command)
    if not submit:return commands
    if config.get('launch_blocker'):raise ValueError(config['launch_blocker'])
    if 'evaluate' in phases and config.get('evaluation_blocker'):raise ValueError(config['evaluation_blocker'])
    for key in {task['implementation'] for task in tasks} | ({'gcn'} if 'evaluate' in phases else set()):
        verify_sources({'implementation':key},workspace)
    checked_inputs=set()
    for task in tasks:
        check_inputs(task,workspace,checked_inputs)
    if phases==['evaluate']:
        for task in tasks:
            require_training_files(run_directory(entry,task,workspace))
    root.mkdir(parents=True,exist_ok=True)
    lockfile=checked_output(output_root,root/'dispatch.lock')
    with lockfile.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        record=root/'submission.json'
        previous=json.loads(record.read_text()) if record.exists() else None
        if previous:
            submitted_phases={job['phase'] for job in previous['jobs']}
            if previous['status']!='submitted' or set(phases)&submitted_phases:
                raise ValueError('Existing submission reservation; inspect it before any retry: '+str(record))
            if previous['design_digest']!=design_digest(entry,workspace_path):
                raise ValueError('Existing submission uses a different design or workspace')
        checked_output(output_root,root/'logs').mkdir(exist_ok=True)
        state=dict(experiment=entry['id'],workspace_sha256=digest(workspace_path),design_digest=design_digest(entry,workspace_path),
                   config_sha256=digest(EXPERIMENTS/entry['directory']/'config.json'),
                   manifest_sha256=digest(EXPERIMENTS/entry['directory']/'manifest.csv'),
                   status='reserved',jobs=previous['jobs'] if previous else [])
        record.write_text(json.dumps(state,indent=2)+'\n')
        try:
            for phase,command in zip(phases,commands):
                if phase=='evaluate' and 'train' in phases:
                    command=[x.replace('<TRAIN_JOB_ID>',state['jobs'][0]['job_id']) for x in command]
                # Persist intent before contacting Slurm. Ambiguous failure blocks resubmission.
                state['pending_command']=command;record.write_text(json.dumps(state,indent=2)+'\n')
                result=subprocess.check_output(command,text=True).strip().split(';')[0]
                if not result.isdigit():raise ValueError('Unrecognized sbatch response; inspect scheduler before retry')
                state['jobs'].append(dict(phase=phase,job_id=result,command=command))
                state['pending_command']=None;record.write_text(json.dumps(state,indent=2)+'\n')
            state['status']='submitted'
        except BaseException:
            state['status']='needs_manual_review';raise
        finally:
            record.write_text(json.dumps(state,indent=2)+'\n')
    return commands


def design_digest(entry, workspace_path):
    directory = EXPERIMENTS/entry['directory']
    paths = [Path(workspace_path),directory/'config.json',directory/'manifest.csv',Path(__file__)]
    paths.extend(EXPERIMENTS/'common'/name for name in ('architecture_sources.json','validate_share_metrics.py'))
    paths.append(EXPERIMENTS/'shareseq/unirep_references.json')
    paths.extend(REPO/'evaluation/shareseq_ma2020/scripts'/name for name in (
        'unirep_cache.py','materialize_run_inputs.py','full_dimension_resource_run.py'))
    return hashlib.sha256(''.join(digest(path) for path in paths).encode()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment',nargs='?')
    parser.add_argument('--list',action='store_true')
    parser.add_argument('--workspace',type=Path,default=EXPERIMENTS/'workspace.example.json')
    parser.add_argument('--phase',choices=('train','evaluate','all'),default='all')
    parser.add_argument('--dry-run',action='store_true',help='Explicit read-only default; no directories or Slurm calls')
    parser.add_argument('--submit',action='store_true')
    parser.add_argument('--task',type=int,default=0,help='Manifest row to show in the plan')
    parser.add_argument('--execute-task',choices=('train','evaluate'),help=argparse.SUPPRESS)
    parser.add_argument('--design-digest',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.list:
        for x in json.loads((EXPERIMENTS/'catalog.json').read_text()):print(x['id']+'\t'+x['status'])
        return
    if args.dry_run and args.submit:parser.error('--dry-run and --submit are mutually exclusive')
    entry,config,tasks=load(args.experiment)
    workspace=json.loads(args.workspace.read_text())
    if args.execute_task:
        if args.submit or args.dry_run:parser.error('Internal execution mode cannot be combined with planning flags')
        index=int(os.environ['SLURM_ARRAY_TASK_ID'])
        if index not in range(len(tasks)):parser.error('Array index outside manifest')
        if config.get('launch_blocker'):raise ValueError(config['launch_blocker'])
        if args.design_digest != design_digest(entry,args.workspace):
            raise ValueError('Launcher, workspace or design changed since submission')
        execute_task(entry,config,tasks[index],workspace,args.execute_task);return
    phases=['train','evaluate'] if args.phase=='all' else [args.phase]
    result=dict(experiment=entry['id'],status=entry['status'],launch_blocker=config.get('launch_blocker'),
                evaluation_blocker=config.get('evaluation_blocker'),expected_tasks=len(tasks),
                historical_submission=config.get('historical_submission'),resources=config['resources'])
    if tasks:
        if args.task not in range(len(tasks)):parser.error('Task outside manifest')
        result['task']=task_plan(entry,config,tasks[args.task],workspace)
        result['submission_commands']=submit_plan(entry,config,tasks,args.workspace,workspace,phases,submit=args.submit)
    elif args.submit:raise ValueError('Historical/planned experiment has no dispatchable design')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    try:main()
    except (ValueError,KeyError) as error:
        raise SystemExit(str(error))
