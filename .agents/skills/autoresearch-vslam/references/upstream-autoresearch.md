# Upstream Autoresearch Notes

Source repository:

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch)
- inspected at GitHub tree commit `228791fb499afffb54b46200aca536f79142f117`

Key upstream files:

- [README.md](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/README.md)
- [program.md](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/program.md)
- [prepare.py](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/prepare.py)
- [train.py](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/train.py)

## Core Upstream Mechanics

Upstream autoresearch is built around a very small research loop:

1. freeze one evaluation harness
2. edit one mutable file
3. run one experiment
4. extract one primary metric
5. keep or discard the change
6. log the outcome in `results.tsv`

The important structural ideas are:

- a tiny mutable surface
- a fixed, trusted evaluator
- comparable experiments
- lightweight experiment logging
- autonomous iteration without waiting for the human after setup

## Why A Direct Port Does Not Fit This Repo

PRML VSLAM is not a single-file training harness:

- it has multiple packages and multiple valid evaluation surfaces
- it has source-of-truth requirements docs that must stay aligned
- it forbids destructive git rollback flows
- it uses `.agents` backlog files as repo memory
- it has expensive validation surfaces such as `make ci`

Because of that, the local adaptation changes four major things:

1. The loop is bounded.
2. The mutable surface is declared per run.
3. Trial branches replace destructive resets.
4. The research brief freezes both metrics and immutable surfaces.

## Mapping To PRML VSLAM

Upstream concept -> PRML VSLAM adaptation

- `prepare.py` immutable harness -> frozen evaluation commands plus frozen docs/contracts
- `train.py` mutable file -> a declared mutable module cluster
- `val_bpb` -> task-specific primary metric
- `results.tsv` -> `.logs/autoresearch/<tag>/results.tsv`
- infinite loop -> explicit run budget

## Typical Local Metrics

- targeted `pytest` pass/fail
- `make loc` deltas for simplification
- `trajectory_metrics.json` values for trajectory-evaluation work
- artifact existence and shape checks for planner/dataset work
- `make ci` as final acceptance, not per-trial default
