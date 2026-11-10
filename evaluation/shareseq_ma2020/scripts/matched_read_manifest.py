#!/usr/bin/env python
import csv,shlex,sys
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"manifests/matched_subsample_manifest.csv"; rows=list(csv.DictReader(open(p)))
i=int(sys.argv[1]); r=rows[i]
if sys.argv[2]=="shell":
    for k,v in r.items(): print(f"{k}={shlex.quote(v)}")
