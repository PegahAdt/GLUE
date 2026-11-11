#!/usr/bin/env python3
"""Restore byte-exact historical workflows into a new directory; never execute them."""
import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def render(item):
    source = REPO / item['template']
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != item['template_sha256']:
        raise ValueError('Template integrity failure: ' + str(source))
    text = raw.decode()
    for token, value in item['replacements'].items():
        text = text.replace(token, value)
    data = text.encode()
    if hashlib.sha256(data).hexdigest() != item['sha256']:
        raise ValueError('Snapshot reconstruction failure: ' + item['path'])
    return data


def restore(snapshot, destination):
    items = json.loads((REPO/'experiments/common/workflow_snapshots.json').read_text())
    prefix = snapshot.rstrip('/') + '/'
    selected = [item for item in items if item['path'].startswith(prefix)]
    if not selected:
        raise ValueError('Unknown snapshot; specify an original workflow directory')
    destination = Path(destination).resolve()
    if REPO == destination or REPO in destination.parents:
        raise ValueError('Restoration belongs outside the code checkout')
    rendered = [(item['path'][len(prefix):], render(item), item.get('executable',False)) for item in selected]
    destination.mkdir(parents=True, exist_ok=False)
    for relative, data, executable in rendered:
        path = destination/relative
        if destination not in path.resolve().parents:
            raise ValueError('Unsafe snapshot path')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if executable:
            path.chmod(path.stat().st_mode | 0o111)
    return len(selected)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', help='e.g. evaluation/gat_tuning_10x/screen_v2/configs/lr_0p001/workflow')
    parser.add_argument('destination', type=Path, help='New external directory, which must not exist')
    args = parser.parse_args()
    print('Restored {} exact files; historical launch compatibility is not implied.'.format(restore(args.snapshot, args.destination)))
