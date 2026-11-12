#!/usr/bin/env python
"""Submit full training only after smoke succeeds, followed by CPU evaluation."""
import json
import subprocess

from common import EXPERIMENT,sha,save_json,verify_freeze,validate_manifest


def submit(script,extra=None):
    result=subprocess.run(['sbatch','--parsable']+(extra or [])+[str(script)],check=True,stdout=subprocess.PIPE,text=True)
    return result.stdout.strip().split(';')[0]


def main():
    verify_freeze();validate_manifest()
    smoke=json.loads((EXPERIMENT/'validation/smoke_success.json').read_text())
    tests=json.loads((EXPERIMENT/'validation/tests.json').read_text())
    if smoke['status']!='passed' or not smoke['evaluation_supports_gcn_without_gates'] or tests['status']!='passed':
        raise ValueError('Successful GCN smoke and automated tests are required before array submission')
    if smoke['frozen_inputs_sha256']!=sha(EXPERIMENT/'validation/frozen_inputs.json'):
        raise ValueError('Smoke used a different frozen configuration')
    path=EXPERIMENT/'submission.json'
    record=json.loads(path.read_text()) if path.exists() else {}
    if record.get('training_array_job_id'):
        print('Training already submitted: '+record['training_array_job_id'],flush=True)
    else:
        record.update(training_array_job_id=submit(EXPERIMENT/'train_array.sbatch'),smoke_job_id=smoke['job_id'],
            frozen_inputs_sha256=smoke['frozen_inputs_sha256'],n_training_tasks=15,concurrency=3)
        save_json(path,record)
    if not record.get('evaluation_job_id'):
        record['evaluation_job_id']=submit(EXPERIMENT/'evaluate.sbatch',[
            '--dependency=afterok:'+record['training_array_job_id'],'--kill-on-invalid-dep=yes'])
        save_json(path,record)
    print(json.dumps(record,indent=2),flush=True)


if __name__=='__main__':main()
