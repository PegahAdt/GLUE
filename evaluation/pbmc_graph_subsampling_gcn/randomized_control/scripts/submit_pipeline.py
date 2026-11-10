"""Submit only three new runs after smoke; depend on both arrays for evaluation."""
import fcntl
import json
import subprocess
from common import BASE,EXPERIMENT,sha,save_json,verify_freeze,validate_manifest


def submit(script,extra=None):
    result=subprocess.run(['sbatch','--parsable']+(extra or [])+[str(script)],check=True,stdout=subprocess.PIPE,text=True)
    return result.stdout.strip().split(';')[0]


def main():
    verify_freeze();validate_manifest();validate_manifest(EXPERIMENT/'combined_manifest.csv')
    smoke=json.loads((EXPERIMENT/'validation/smoke_success.json').read_text())
    tests=json.loads((EXPERIMENT/'validation/tests.json').read_text())
    if smoke['status']!='passed' or not smoke['evaluation_supports_gcn_without_gates'] or tests['status']!='passed':
        raise ValueError('Successful randomized GCN smoke and tests required')
    if smoke['frozen_inputs_sha256']!=sha(EXPERIMENT/'validation/frozen_inputs.json'):
        raise ValueError('Smoke validated different inputs/code')
    original=json.loads((BASE/'submission.json').read_text())
    if original['training_array_job_id']!='64840335' or original['evaluation_job_id']!='64840336':
        raise ValueError('Original experiment job identities changed')
    # Lock protects against duplicate submissions by simultaneous dispatch/manual calls.
    with (EXPERIMENT/'submission.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        path=EXPERIMENT/'submission.json'
        record=json.loads(path.read_text()) if path.exists() else {}
        if not record.get('training_array_job_id'):
            for row in validate_manifest().itertuples(index=False):
                from pathlib import Path
                if Path(row.run_dir).exists(): raise ValueError('Refuse to overwrite existing randomized training output')
            record.update(training_array_job_id=submit(EXPERIMENT/'train_array.sbatch'),smoke_job_id=smoke['job_id'],
                frozen_inputs_sha256=smoke['frozen_inputs_sha256'],n_training_tasks=3,concurrency=3,
                existing_training_array_job_id='64840335',existing_evaluation_job_id='64840336',
                combined_gcn_runs=18,conditions=6,seeds=[0,1,2])
            save_json(path,record)
        if not record.get('evaluation_job_id'):
            dependency='afterok:64840335:'+record['training_array_job_id']
            record['evaluation_job_id']=submit(EXPERIMENT/'evaluate.sbatch',[
                '--dependency='+dependency,'--kill-on-invalid-dep=yes'])
            record['evaluation_dependency']=dependency
            record['report_directory']=str(BASE/'reports'/('combined_randomized_job_'+record['evaluation_job_id']))
            save_json(path,record)
        print(json.dumps(record,indent=2),flush=True)


if __name__=='__main__':main()
