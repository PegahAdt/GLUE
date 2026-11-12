#!/usr/bin/env python
"""Manifest orchestration for the existing full SHARE-seq training pipeline."""

import argparse
import csv
import fcntl
import importlib.util
import io
import itertools
import json
import os
from pathlib import Path
import runpy
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SHARED = REPO.parent / "GLUE/evaluation/shareseq_ma2020"
ENV = REPO.parent / "GLUE/conda"
MANIFEST = ROOT / "manifests/all_runs.csv"
PREFLIGHT = ROOT / "preflight.json"
DIMS_A = (16, 32, 50, 64, 100, 128, 200, 256, 384, 512, 768, 1024)
DIMS_B = (1536, 2048, 3072, 4096)
GATES = ("0.25", "0.50", "0.75", "0.95")
SEEDS = (0, 1, 2)
TRAINING = REPO / "evaluation/workflow/scripts/run_GLUE.py"
RUNNER = SHARED / "scripts/full_dimension_resource_run.py"
EXTRACTOR = SHARED / "scripts/extract_gates.py"
SPEC = importlib.util.spec_from_file_location("full_dimension", SHARED / "scripts/full_dimension.py")
FULL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FULL)
ARTIFACTS = (
    "final.dill", "run_info.yaml", "requested_configuration.json", "run_configuration.json",
    "rna_latent.csv", "atac_latent.csv", "feature_latent.csv", "resource_usage.json",
    "gates.csv", "gates_nonself.csv.gz", "gate_summary.yaml", "gate_diagnostics.yaml",
    "run_GLUE.log", "extract_gates.log", "provenance.json",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def read_rows(path=MANIFEST):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def atomic_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def immutable_text(path, content):
    if path.exists():
        require(path.read_text() == content, f"Refusing to replace different configuration: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def csv_text(rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def verify_manifest(rows):
    expected = set(itertools.product(DIMS_A + DIMS_B, GATES, SEEDS))
    actual = [(int(row["latent_dim"]), row["gate_init"], int(row["model_seed"])) for row in rows]
    require(len(rows) == len(set(actual)) == 192 and set(actual) == expected, "Sweep must contain exactly the 192 unique requested combinations")
    require(len({row["output_directory"] for row in rows}) == 192, "Duplicate output paths")
    require(len({row["run_id"] for row in rows}) == 192, "Duplicate run IDs")
    for array, dimensions, count in (("A", DIMS_A, 144), ("B", DIMS_B, 48)):
        subset = [row for row in rows if row["array"] == array]
        require(len(subset) == count, f"Wrong task count in array {array}")
        require([int(row["task_id"]) for row in subset] == list(range(count)), "Array indices must be contiguous")
        require({int(row["latent_dim"]) for row in subset} == set(dimensions), "Wrong array dimensions")
    for dimension in DIMS_A + DIMS_B:
        subset = [row for row in rows if int(row["latent_dim"]) == dimension]
        require(len(subset) == 12 and {row["gate_init"] for row in subset} == set(GATES), "Incomplete dimension")
        for gate in GATES:
            require({int(row["model_seed"]) for row in subset if row["gate_init"] == gate} == set(SEEDS), "Incomplete seed group")
    for row in rows:
        expected_path = ROOT / f"dim_{row['latent_dim']}" / f"gateinit_{row['gate_init']}" / f"seed_{row['model_seed']}"
        require(Path(row["output_directory"]) == expected_path, "Noncanonical output directory")
        require(row["architecture"] == "gated" and row["cell_count"] == "32231" and float(row["lam_keep"]) == 0, "Changed fixed experiment setting")
    for key in ("graph_path", "graph_checksum", "rna_path", "atac_path", "cell_manifest_path", "git_commit"):
        require(len({row[key] for row in rows}) == 1, f"Varying fixed input: {key}")


def prepare():
    base = next(row for row in read_rows(FULL.MAN) if row["architecture"] == "gated" and row["latent_dim"] == "50")
    commit = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    rows = []
    for array, dimensions in (("A", DIMS_A), ("B", DIMS_B)):
        for task_id, (dimension, gate, seed) in enumerate(itertools.product(dimensions, GATES, SEEDS)):
            output = ROOT / f"dim_{dimension}" / f"gateinit_{gate}" / f"seed_{seed}"
            row = dict(base)
            row.update(run_id=f"gated_full_dim{dimension}_gate{gate}_seed{seed}", latent_dim=str(dimension),
                       gate_init=gate, model_seed=str(seed), output_directory=str(output),
                       expected_checkpoint=str(output / "final.dill"), replicate_source="shareseq_gate_stability",
                       reuse_source="", training_state="pending", metric_state="not_requested",
                       gate_analysis_state="pending", slurm_job_id="", runtime="", git_commit=commit,
                       array=array, task_id=str(task_id))
            rows.append(row)
    verify_manifest(rows)
    immutable_text(MANIFEST, csv_text(rows))
    for array in ("A", "B"):
        immutable_text(ROOT / f"manifests/array_{array}.csv", csv_text([row for row in rows if row["array"] == array]))
    (ROOT / "logs").mkdir(exist_ok=True)
    print("Verified and prepared 192 combinations: A=144, B=48", flush=True)


def training_command(row):
    output = Path(row["output_directory"])
    command = [str(ENV / "bin/python"), "-u", str(RUNNER)]
    values = dict(FULL.FIXED, random_seed=int(row["model_seed"]), dim=int(row["latent_dim"]),
                  input_rna=output / "rna.h5ad", input_atac=output / "atac.h5ad", prior=row["graph_path"],
                  train_dir=output, output_rna=output / "rna_latent.csv", output_atac=output / "atac_latent.csv",
                  output_feature=output / "feature_latent.csv", run_info=output / "run_info.yaml",
                  graph_encoder="gated", gate_init=row["gate_init"], lam_keep=row["lam_keep"])
    for key, value in values.items():
        command.append("--" + key.replace("_", "-"))
        if value is not True:
            command.append(str(value))
    return command


def parse_commands(rows):
    parser = runpy.run_path(str(TRAINING), run_name="shareseq_training_arguments")["parse_args"]
    configurations = {}
    original_argv = sys.argv
    try:
        for row in rows:
            sys.argv = [str(TRAINING)] + training_command(row)[3:]
            args = vars(parser())
            for key, value in dict(FULL.FIXED, random_seed=int(row["model_seed"])).items():
                require(args[key] == value, f"Changed training setting: {key}")
            require(args["dim"] == int(row["latent_dim"]) and args["gate_init"] == float(row["gate_init"]), "Wrong command parameters")
            require(args["graph_encoder"] == "gated" and args["lam_keep"] == 0, "Wrong architecture")
            configurations[row["run_id"]] = {key: str(value) if isinstance(value, Path) else value for key, value in args.items()}
    finally:
        sys.argv = original_argv
    return configurations


def check_hashes(hashes):
    for path, digest in hashes.items():
        require(Path(path).is_file() and FULL.sha(path) == digest, f"Integrity check failed: {path}")


def source_paths():
    return [Path(__file__).resolve(), ROOT / "analyze.py", ROOT / "test_experiment.py", ROOT / "environment.sh",
            ROOT / "submit.sh", ROOT / "analyze.sh", *sorted((ROOT / "slurm").glob("*.sbatch")),
            SHARED / "scripts/full_dimension.py", RUNNER, EXTRACTOR,
            SHARED / "scripts/materialize_run_inputs.py"]


def environment_check():
    require(os.environ.get("MKL_THREADING_LAYER") == "GNU", "Source environment.sh to select the GNU MKL threading layer before importing numerical libraries")
    import scglue
    require(Path(scglue.__file__).resolve() == (REPO / "scglue/__init__.py").resolve(), f"Wrong scglue: {scglue.__file__}")
    require(Path(sys.executable).resolve() == (ENV / "bin/python").resolve(), "Wrong Python environment")
    require(not os.environ.get("DIMENSION_SMOKE"), "Shortened training is forbidden")
    require(not sys.flags.optimize, "Validation assertions must be enabled")
    return {"python": sys.executable, "scglue": scglue.__file__, "mkl_threading_layer": os.environ["MKL_THREADING_LAYER"]}


def preflight():
    rows = read_rows()
    verify_manifest(rows)
    for array in ("A", "B"):
        require(read_rows(ROOT / f"manifests/array_{array}.csv") == [row for row in rows if row["array"] == array], "Array manifest differs from master")
    previous = json.loads(FULL.AUDIT.read_text())
    for name in ("input_hashes", "unirep_hashes", "gated_code_hashes"):
        check_hashes(previous[name])
        print(f"Previous {name} verified", flush=True)
    base = rows[0]
    ids = Path(base["cell_manifest_path"]).read_text().splitlines()
    require(len(ids) == len(set(ids)) == 32231, "Invalid canonical full cell set")
    for key in ("rna_path", "atac_path", "graph_path", "cell_manifest_path"):
        require(base[key] in previous["input_hashes"], f"Input differs from previous experiment: {key}")
    require(base["graph_checksum"] == previous["input_hashes"][base["graph_path"]], "Graph checksum differs")
    for modality in ("rna", "atac"):
        FULL.ordered(base[modality + "_path"], ids)
    import anndata as ad
    sys.path.insert(0, str(SHARED / "scripts"))
    from unirep_cache import validate_rep
    for modality, path in previous["unireps"].items():
        data = ad.read_h5ad(base[modality + "_path"], backed="r")
        try:
            validate_rep(Path(path), data, ids)
        finally:
            data.file.close()
    environment = environment_check()
    configurations = parse_commands(rows)
    print("Canonical ordering and all 192 training commands verified", flush=True)
    legacy = next(row for row in read_rows(FULL.MAN) if row["architecture"] == "gated" and row["latent_dim"] == "16")
    FULL.validate(legacy)
    subprocess.run([sys.executable, "-m", "unittest", "-v", "test_experiment"], cwd=ROOT, check=True)
    import networkx as nx
    graph = nx.read_graphml(base["graph_path"])
    endpoints = sorted((source, target) for source, target in graph.edges() if source != target)
    require(endpoints and len(endpoints) == len(set(endpoints)), "Nonunique guidance graph endpoints")
    edges = pd.DataFrame(endpoints, columns=["source", "target"])
    edges.insert(0, "edge_id", np.arange(len(edges)))
    immutable_text(ROOT / "manifests/edges.csv", edges.to_csv(index=False))
    for script in [ROOT / "environment.sh", ROOT / "submit.sh", ROOT / "analyze.sh", *sorted((ROOT / "slurm").glob("*.sbatch"))]:
        subprocess.run(["bash", "-n", str(script)], check=True)
    files = source_paths() + sorted((ROOT / "manifests").glob("*.csv"))
    hashes = {**previous["input_hashes"], **previous["unirep_hashes"], **previous["gated_code_hashes"],
              **{str(path): FULL.sha(path) for path in files}}
    atomic_json(PREFLIGHT, dict(passed=True, checked_at=now(), total=192, array_A=144, array_B=48,
                              canonical_cells=len(ids), nonself_edges=len(edges), environment=environment,
                              legacy_run_validated=legacy["run_id"], hashes=hashes, configurations=configurations))
    print("PREFLIGHT PASSED: 192 runs, A=144, B=48; legacy and nondefault validator tests passed", flush=True)


def verified_preflight():
    audit = json.loads(PREFLIGHT.read_text())
    require(audit["passed"] and audit["total"] == 192, "No successful preflight")
    check_hashes(audit["hashes"])
    environment_check()
    return audit


def nonself_gates(output):
    gates = pd.read_csv(output / "gates.csv")
    require(set(gates.columns) == {"source", "target", "logit", "gate", "is_self_loop"}, "Unexpected gate schema")
    require(gates["is_self_loop"].isin([True, False]).all(), "Invalid self-loop flags")
    loops = gates["is_self_loop"].astype(bool)
    require((loops == (gates.source == gates.target)).all(), "Self-loop flag disagrees with endpoints")
    nonself = gates.loc[~loops].copy()
    require(not gates.duplicated(["source", "target"]).any(), "Duplicate gate endpoints")
    require(np.isfinite(nonself[["logit", "gate"]].values).all(), "Nonfinite non-self-loop gates")
    require(nonself.gate.between(0, 1).all(), "Gate outside [0, 1]")
    from scipy.special import expit
    require(np.allclose(expit(nonself.logit), nonself.gate, rtol=1e-6, atol=1e-7), "Gate/logit disagreement")
    edges = pd.read_csv(ROOT / "manifests/edges.csv")
    merged = edges.merge(nonself, on=["source", "target"], how="outer", validate="one_to_one", indicator=True)
    require(merged["_merge"].eq("both").all(), "Gate edge universe differs from guidance graph")
    return merged.drop(columns="_merge").sort_values("edge_id").reset_index(drop=True)


def validate_outputs(row, audit):
    output = Path(row["output_directory"])
    FULL.validate(row)
    for name in ARTIFACTS:
        require((output / name).is_file() and (output / name).stat().st_size > 0, f"Missing {name}")
    for name in ("stdout.log", "stderr.log"):
        require((output / name).is_file(), f"Missing SLURM {name}")
    require(json.loads((output / "requested_configuration.json").read_text()) == row, "Manifest row changed")
    require(json.loads((output / "run_configuration.json").read_text()) == audit["configurations"][row["run_id"]], "Training configuration changed")
    resource = json.loads((output / "resource_usage.json").read_text())
    require(resource["success"] and not resource["smoke_only"], "Training did not finish normally")
    expected = nonself_gates(output)
    observed = pd.read_csv(output / "gates_nonself.csv.gz")
    pd.testing.assert_frame_equal(expected, observed, check_dtype=False, check_exact=False, rtol=1e-7, atol=1e-8)
    return {name: FULL.sha(output / name) for name in ARTIFACTS}


def validate_complete(row, audit):
    output = Path(row["output_directory"])
    marker = json.loads((output / "COMPLETED.json").read_text())
    require(marker["manifest_row"] == row, "Completion marker configuration mismatch")
    require(marker["artifacts"] == validate_outputs(row, audit), "Completed output hash mismatch")


def run_task(array, index):
    require(index >= 0, "Negative task index")
    row = read_rows(ROOT / f"manifests/array_{array}.csv")[index]
    print(json.dumps(dict(date=now(), hostname=os.uname().nodename, slurm_job_id=os.environ.get("SLURM_JOB_ID"),
                          array_task_id=index, manifest_row=row, latent_dim=row["latent_dim"],
                          gate_init=row["gate_init"], model_seed=row["model_seed"], python=sys.executable), indent=2), flush=True)
    audit = verified_preflight()
    output = Path(row["output_directory"])
    (ROOT / "locks").mkdir(exist_ok=True)
    with (ROOT / "locks" / (row["run_id"] + ".lock")).open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (output / "COMPLETED.json").exists():
            validate_complete(row, audit)
            print("SKIP validated completed run " + row["run_id"], flush=True)
            return
        trained = False
        if output.exists():
            try:
                FULL.validate(row)
                require(json.loads((output / "requested_configuration.json").read_text()) == row, "Metadata mismatch")
                trained = True
            except Exception as error:
                archive = ROOT / "incomplete" / row["run_id"] / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                archive.parent.mkdir(parents=True, exist_ok=True)
                output.rename(archive)
                print(f"Preserved incomplete attempt at {archive}: {error}", flush=True)
        output.mkdir(parents=True, exist_ok=True)
        for modality in ("rna", "atac"):
            link = output / f"{modality}.h5ad"
            if not link.exists():
                link.symlink_to(row[modality + "_path"])
            FULL.ordered(link, Path(row["cell_manifest_path"]).read_text().splitlines())
        for suffix, name in (("out", "stdout.log"), ("err", "stderr.log")):
            target = ROOT / "logs" / f"array_{array}_{os.environ['SLURM_ARRAY_JOB_ID']}_{index}.{suffix}"
            require(target.is_file(), f"Missing SLURM log: {target}")
            link = output / name
            if not link.exists() and not link.is_symlink():
                link.symlink_to(target)
        if not trained:
            atomic_json(output / "requested_configuration.json", row)
            atomic_json(output / "run_configuration.json", audit["configurations"][row["run_id"]])
            atomic_json(output / "provenance.json", dict(preflight_sha256=FULL.sha(PREFLIGHT), hashes=audit["hashes"],
                                                        manifest_row=row, command=training_command(row), started_at=now(),
                                                        slurm_job_id=os.environ.get("SLURM_JOB_ID")))
            print("COMMAND " + shlex.join(training_command(row)), flush=True)
            with (output / "run_GLUE.log").open("w") as log:
                subprocess.run(training_command(row), cwd=SHARED, check=True, stdout=log, stderr=subprocess.STDOUT)
        FULL.validate(row)
        with (output / "extract_gates.log").open("w") as log:
            subprocess.run([str(ENV / "bin/python"), str(EXTRACTOR), "--smoke", str(output)],
                           cwd=SHARED, check=True, stdout=log, stderr=subprocess.STDOUT)
            log.write("Canonical final-checkpoint gate extraction completed\n")
        nonself_gates(output).to_csv(output / "gates_nonself.csv.gz", index=False)
        summary_path = output / "gate_summary.yaml"
        summary = yaml.safe_load(summary_path.read_text())
        summary.update(run_id=row["run_id"], latent_dim=int(row["latent_dim"]), gate_init=float(row["gate_init"]), model_seed=int(row["model_seed"]))
        summary_path.write_text(yaml.safe_dump(summary))
        hashes = validate_outputs(row, audit)
        atomic_json(output / "COMPLETED.json", dict(completed_at=now(), manifest_row=row, artifacts=hashes))
        print("COMPLETED " + row["run_id"], flush=True)


def submit():
    verified_preflight()
    record = ROOT / "submitted_jobs.json"
    (ROOT / "locks").mkdir(exist_ok=True)
    with (ROOT / "locks/submit.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        jobs = json.loads(record.read_text()) if record.exists() else {}
        for array in ("A", "B"):
            if array in jobs:
                print(f"Already submitted array {array}: {jobs[array]['job_id']}", flush=True)
                continue
            command = ["sbatch", "--parsable", str(ROOT / f"slurm/array_{array.lower()}.sbatch")]
            result = subprocess.check_output(command, cwd=ROOT, text=True).strip()
            job_id = result.split(";")[0]
            require(job_id.isdigit(), f"Unexpected sbatch response: {result}")
            jobs[array] = dict(job_id=job_id, submitted_at=now(), tasks=144 if array == "A" else 48,
                               command=command, preflight_sha256=FULL.sha(PREFLIGHT))
            atomic_json(record, jobs)
            print(f"Submitted array {array}: job {job_id}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "preflight", "submit", "run"))
    parser.add_argument("array", choices=("A", "B"), nargs="?")
    parser.add_argument("index", type=int, nargs="?")
    args = parser.parse_args()
    if args.action == "run":
        require(args.array is not None and args.index is not None, "Array and task index required")
        run_task(args.array, args.index)
    else:
        globals()[args.action]()


if __name__ == "__main__":
    main()
