#!/usr/bin/env python3
"""Read-only repository consistency checks. Never import scientific packages or launch jobs."""
import argparse
import ast
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
KNOWN_SYNTAX = {'experiments/RegInf/s06_genomic_tracks.py'}
KNOWN_EXTERNAL_LINKS = {'evaluation/custom', 'experiments/Atlas/custom'}
DOCUMENTATION_DECISIONS = {'documentation_consolidated', 'integration_ignore_policy',
    'documentation_only_expired_URL_redaction; original in Git ancestry'}
SECRET_PATTERNS = {
    'private_key': rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
    'github_token': rb'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{40,})',
    'aws_access_id': rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'slack_token': rb'\bxox[baprs]-[0-9A-Za-z-]{15,}',
    'credential_url': rb'https?://[^\s/"<>:@]+:[^\s/"<>@]+@',
}


def sha(path):
    p=Path(path)
    data=os.readlink(p).encode() if p.is_symlink() else p.read_bytes()
    return hashlib.sha256(data).hexdigest()


def profile_failures(root, profile):
    failures=[]
    for rel,expected in profile['files'].items():
        p=Path(root)/profile['root']/rel
        # Model/helper aliases refer to file contents, not the symlink's target text.
        actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
        if actual!=expected:failures.append(rel)
    return failures


def new_documents(root):
    names=['README.md','CONTRIBUTIONS.md','THESIS_EXPERIMENTS.md','REPRODUCIBILITY.md',
           'ARCHITECTURE.md','LICENSE_AND_ATTRIBUTION.md','results/README.md','experiments/README.md',
           'implementations/README.md','environments/README.md','historical/reproduction/README.md']
    catalog=json.loads((root/'experiments/catalog.json').read_text())
    names += ['experiments/'+x['directory']+'/README.md' for x in catalog]
    names += ['experiments/pbmc/gated_stage_b_plan/README.md']
    names += [str(p.relative_to(root)) for p in (root/'docs/research').glob('*.md')]
    names += [str(p.relative_to(root)) for p in (root/'implementations').glob('*/README.md')]
    return set(names)


def markdown_issues(root, name, pending_report=False):
    problems=[];links=0
    for value in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)',(root/name).read_text(errors='replace')):
        value=value.strip('<>')
        if re.match(r'(?:https?://|mailto:)',value):continue
        path,_,fragment=value.partition('#')
        if not path:continue
        links+=1
        p=(root/name).parent/path
        if pending_report and p.resolve()==root/'provenance/validation_summary.json':continue
        if not p.exists():problems.append(dict(document=name,target=value))
        elif fragment and p.suffix=='.md':
            text=p.read_text();headings=re.findall(r'^#+\s+(.+)$',text,re.M)
            anchors={re.sub(r'[^\w\s-]','',h).lower().replace(' ','-') for h in headings}
            anchors.update(re.findall(r'<a\s+id="([^"]+)"',text))
            if fragment not in anchors:problems.append(dict(document=name,target=value,reason='missing anchor'))
    return links,problems


def validate(root=ROOT, with_history=False, pending_report=False):
    root=Path(root).resolve();errors=[];counts={};warnings={}
    sources=json.loads((root/'provenance/integration_sources.json').read_text())
    profiles=json.loads((root/'provenance/implementation_versions.json').read_text())
    for name,profile in profiles.items():
        wrong=profile_failures(root,profile)
        if wrong:errors.append(dict(kind='implementation_hash',profile=name,paths=wrong))
    canonical=json.loads((root/'experiments/common/architecture_sources.json').read_text())
    for name,entry in canonical.items():
        if not all(profiles[name]['files'].get(p)==expected for p,expected in entry['files'].items()):
            errors.append(dict(kind='canonical_fingerprint_closure',profile=name))
    counts['implementation_profiles']=len(profiles)
    counts['pinned_implementation_files']=sum(len(p['files']) for p in profiles.values())
    preserved=0;history_cache={}
    for item in sources['records']:
        target=item['destination'];decision=item['decision']
        if target is not None and decision not in DOCUMENTATION_DECISIONS:
            p=root/target
            if (not p.exists() and not p.is_symlink()) or sha(p)!=item['sha256']:
                errors.append(dict(kind='preservation_hash',path=target,source=item['source']))
            elif not p.is_symlink() and bool(p.stat().st_mode & 0o111)!=(item['mode']=='100755'):
                errors.append(dict(kind='preservation_mode',path=target))
            preserved+=1
        if with_history and item['git_blob'] not in history_cache:
            data=subprocess.check_output(['git','--no-optional-locks','-C',str(root),'cat-file','blob',item['git_blob']])
            history_cache[item['git_blob']]=hashlib.sha256(data).hexdigest()
        if with_history and history_cache[item['git_blob']]!=item['sha256']:
            errors.append(dict(kind='original_git_blob',source=item['source'],path=item['original_path']))
    counts['source_routes']=len(sources['records']);counts['byte_preserved_routes']=preserved
    counts['original_git_blobs_checked']=len(history_cache)

    catalog=json.loads((root/'experiments/catalog.json').read_text())
    mapped=json.loads((root/'provenance/experiment_map.json').read_text())
    ids=[x['id'] for x in mapped]
    if len(ids)!=len(set(ids)) or not set(x['id'] for x in catalog)<=set(ids):errors.append(dict(kind='catalog_mapping'))
    missing_map=[];manifest_rows={}
    for row in mapped:
        for field in ['train','evaluate','configuration','plots','prep_entrypoints']:
            for path in row[field]:
                if not (root/path).exists():missing_map.append(dict(id=row['id'],field=field,path=path))
    for entry in catalog:
        directory=root/'experiments'/entry['directory']
        for name in ['README.md','config.json']:
            if not (directory/name).is_file():errors.append(dict(kind='missing_catalog_file',path=str((directory/name).relative_to(root))))
        manifest=directory/'manifest.csv'
        if manifest.is_file():
            with manifest.open(newline='') as handle:rows=list(csv.DictReader(handle))
            if [int(r['task_id']) for r in rows]!=list(range(len(rows))):errors.append(dict(kind='manifest_task_order',id=entry['id']))
            manifest_rows[entry['id']]=len(rows)
    with (root/'experiments/pbmc/latent_dimensions/manifest.csv').open(newline='') as handle:rows=list(csv.DictReader(handle))
    identities=[]
    for row in rows:
        match=re.fullmatch(r'subsample_size:(\d+)-subsample_seed:(\d+)',Path(row['rna_path']).parent.name)
        if not match:errors.append(dict(kind='dimension_path_identity'));continue
        size,seed=map(int,match.groups());identities.append((row['architecture'],size,int(row['dim']),seed,int(row['model_seed'])))
    expected={(a,n,d,0,0) for a in ['gcn','gat','gated'] for n in [2000,8000] for d in [16,32,50,64,100]}
    if len(identities)!=30 or len(set(identities))!=30 or set(identities)!=expected:errors.append(dict(kind='dimension_coverage'))
    counts.update(catalog_entries=len(catalog),experiment_map_records=len(mapped),manifest_rows=manifest_rows,pbmc_dimension_conditions=len(identities))
    warnings['external_planned_or_missing_mapping_targets']=missing_map

    new_docs=new_documents(root);links=0
    for name in sorted(new_docs):
        if not (root/name).is_file():errors.append(dict(kind='missing_research_document',path=name));continue
        n,problems=markdown_issues(root,name,pending_report);links+=n
        errors += [dict(kind='research_document_link',**p) for p in problems]
    counts['new_research_documents']=len(new_docs);counts['new_document_local_links']=links

    syntax=[];python_count=bash_count=json_count=0;inherited_links=[];dangling=[];large=[];secrets=[];artifacts=[]
    for p in sorted(root.rglob('*')):
        rel=str(p.relative_to(root))
        if rel=='.git' or any(x in {'__pycache__','.pytest_cache'} for x in p.relative_to(root).parts):continue
        if p.is_symlink():
            if not p.exists():dangling.append(rel)
            if p.resolve()!=root and root not in p.resolve().parents and rel not in KNOWN_EXTERNAL_LINKS:
                errors.append(dict(kind='external_symlink',path=rel))
            if p.is_dir() or not p.exists():continue
        if not p.is_file():continue
        data=p.read_bytes()
        if len(data)>5*1024*1024:large.append(dict(path=rel,bytes=len(data)))
        if p.suffix.lower() in {'.h5ad','.dill','.pt','.pth','.pkl','.bam','.fastq','.out','.err','.log','.pdf'}:artifacts.append(rel)
        for label,pattern in SECRET_PATTERNS.items():
            if re.search(pattern,data):secrets.append(dict(path=rel,category=label))
        if p.suffix=='.py':
            python_count+=1
            try:ast.parse(data.decode(),filename=rel)
            except SyntaxError as exc:syntax.append(dict(path=rel,line=exc.lineno,message=exc.msg))
        if p.suffix in {'.sh','.sbatch'} or data.startswith((b'#!/bin/bash',b'#!/usr/bin/env bash')):
            bash_count+=1
            result=subprocess.run(['bash','-n',str(p)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            if result.returncode:errors.append(dict(kind='bash_syntax',path=rel,detail=result.stderr.decode()))
        if p.suffix=='.json' and rel!='.vscode/launch.json':
            json_count+=1
            try:json.loads(data)
            except (ValueError,UnicodeError):errors.append(dict(kind='json_parse',path=rel))
        if p.suffix=='.md' and rel not in new_docs:
            _,problems=markdown_issues(root,rel,pending_report);inherited_links.extend(problems)
    if {x['path'] for x in syntax}!=KNOWN_SYNTAX:errors.append(dict(kind='unexpected_python_syntax',found=syntax))
    if set(dangling)-KNOWN_EXTERNAL_LINKS:errors.append(dict(kind='unexpected_dangling_symlinks',found=dangling))
    if large:errors.append(dict(kind='large_publication_files',files=large))
    if secrets:errors.append(dict(kind='credential_patterns',findings=secrets))
    if artifacts:errors.append(dict(kind='generated_scientific_artifacts',paths=artifacts))
    warnings.update(inherited_python_syntax=syntax,declared_external_R_symlinks=[
        dict(path=p,resolves=(root/p).exists(),note='packrat/custom is a tracked placeholder, not a bundled installed R library')
        for p in sorted(KNOWN_EXTERNAL_LINKS)],dangling_symlinks=dangling,inherited_document_links=inherited_links,
        runtime='No scientific execution, GPU verification or numerical reproduction; historical/frozen external dependencies remain')
    counts.update(python_files_parsed=python_count-len(syntax),python_files_with_inherited_error=len(syntax),bash_syntax_checks=bash_count,json_files_parsed=json_count)
    return dict(status='PASS' if not errors else 'FAIL',scope='Repository consistency only; scientific/GPU reproduction unverified',counts=counts,errors=errors,warnings=warnings)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--with-history',action='store_true',help='Also compare source records against original local Git blobs')
    args=parser.parse_args();result=validate(with_history=args.with_history)
    print(json.dumps(result,indent=2,sort_keys=True));return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    sys.exit(main())
