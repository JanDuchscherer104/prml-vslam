// RESPONSIBILITY: JAN (full-section)

= Benchmark Framework
The implemented benchmark framework was motivated to satisfy the project's two methodological
targets: offline experiments must be reproducible from persisted evidence, while the core components
of the same pipeline must support real-time VSLAM on an incoming phone stream for visualizing
incremental scene updates and allowing an evaluation of the method's real-time performances. In both
settings, the measured object should be the SLAM method and its declared preprocessing, not
incidental file layout, viewer transforms, or repeated copying of RGB-D payloads. A run is therefore
planned as a deterministic sequence of stages, consisting of normalized sources, vSLAM, optional gravity, Sim(3) and ICP
alignment, trajectory metrics, point-cloud & image projection evaluation, and live or export sinks.


#figure(
  image("../../figures/fletcher/pipeline/pipeline_stage_order.png", width: 100%),
  caption: text(size: 9.5pt)[Stage flow with observer fan-out.],
) <fig:framework-contracts>

Artifact-based reproducibility means: stages build their own inputs, the pipeline
records lifecycle and failure provenance, and downstream stages receive only references to the persisted evidence of upstream stages.
Standardized path contracts fix evidence under `input/`, `benchmark/`, `slam/`, `evaluation/trajectory/`,
`reconstruction/`, and `summary/` sub-dirs of the respective run directory. Rerun and UI state receive live observer updates via an event-based fan-out by some of the stages, as illustrated in @fig:framework-contracts.

Streaming preserves the same stage order but moves the runtime boundary to a bounded actor pipeline.
Source and method execution form the hot path: frames are credit-flowed, and RGB, depth, and
point-map arrays travel as transient references instead of repeated copies. Method outputs and
captured frame/keyframe rates and latency enable runtime evaluation; replay can respect timestamps or run
fast-as-possible, and live Record3D uses the same path for incremental visualization and export.
