"""Wrap the unmodified entry point; smoke alone limits Ignite iterations."""
import json, os, runpy, sys, time
from pathlib import Path
import torch
import scglue
impl=Path(os.environ['PYTHONPATH']); assert Path(scglue.__file__).resolve()==(impl/'scglue/__init__.py').resolve()
print('scglue.__file__='+scglue.__file__,flush=True)
assert torch.cuda.is_available(), 'GPU required'
smoke=os.environ.get('DIMENSION_SMOKE')=='1'
if smoke:
 import ignite.engine
 original=ignite.engine.Engine.run
 def short(self,data=None,max_epochs=None,epoch_length=None,**kwargs):
  return original(self,data,max_epochs=1,epoch_length=3,**kwargs)
 ignite.engine.Engine.run=short
out=Path(sys.argv[sys.argv.index('--train-dir')+1]); started=time.time()
torch.cuda.reset_peak_memory_stats()
sys.argv[0]=str(impl/'evaluation/workflow/scripts/run_GLUE.py')
try:
 runpy.run_path(sys.argv[0],run_name='__main__')
 torch.cuda.synchronize()
 result=dict(success=True,smoke_only=smoke,iterations_per_phase=3 if smoke else None,gpu_name=torch.cuda.get_device_name(),gpu_total_bytes=torch.cuda.get_device_properties(0).total_memory,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),wall_seconds=time.time()-started,slurm_job_id=os.environ.get('SLURM_JOB_ID'))
 (out/'resource_usage.json').write_text(json.dumps(result,indent=2))
except BaseException as e:
 (out/'resource_failure.json').write_text(json.dumps(dict(success=False,error=repr(e),smoke_only=smoke,peak_allocated_bytes=torch.cuda.max_memory_allocated()),indent=2)); raise
