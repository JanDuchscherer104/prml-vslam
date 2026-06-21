#import "@preview/booktabs:0.0.4": toprule, midrule, bottomrule

= Appendix: Supplementary Architecture and Artifact Map

== Pipeline Architecture Diagrams

The following diagrams document implementation structure that is useful for reproducibility but too
detailed for the main paper. The main text uses the scientific consequences of these contracts:
deterministic planning, standardized stage handoff, and separation between live diagnostics and
durable artifacts.

#figure(
  image("../../figures/mermaid/pipeline/03-run-config-stage-plan.png", width: 100%),
  caption: [Supplementary architecture: deterministic compilation from experiment configuration to an ordered execution plan.],
) <fig:appendix-run-config-stage-plan>

#figure(
  image("../../figures/mermaid/pipeline/06-stage-result.png", width: 100%),
  caption: [Supplementary architecture: terminal stage handoff and durable artifact persistence.],
) <fig:appendix-stage-result-handoff>

#figure(
  image("../../figures/mermaid/pipeline/07-runtime-updates-visualization.png", width: 100%),
  caption: [Supplementary architecture: live diagnostic updates are separated from durable scientific artifacts.],
) <fig:appendix-runtime-updates-visualization>

== Artifact and Responsibility Map

The artifact map summarizes the implemented framework surfaces in scientific terms. It is retained
as supplementary context for readers who want to reproduce or extend the benchmark, not as an
authorship or speaking-order record.

#figure(
  table(
    columns: (0.76fr, 1.55fr, 1.45fr),
    align: (left, left, left),
    inset: (x: 0.24em, y: 0.21em),
    column-gutter: 0.38em,
    toprule(),
    table.header([Area], [Artifact or contract], [Scientific role]),
    midrule(),
    [Source data],
    [Normalized sequence manifest, observation sequence, timestamps, intrinsics, and prepared references.],
    [Defines what a method may consume and what may be used only for evaluation.],
    [Method execution],
    [Method configuration, normalized trajectory, dense point-cloud artifact, and native extras.],
    [Makes method outputs comparable without erasing native diagnostics.],
    [Trajectory alignment],
    [Alignment metadata, aligned trajectory, reference source, and association policy.],
    [Documents the transformation used before trajectory metrics are interpreted.],
    [Dense geometry],
    [Reference cloud, Sim(3)-placed cloud, ICP-refined cloud, and cloud-alignment metadata.],
    [Separates cloud placement from final dense-quality scoring.],
    [Visualization],
    [Neutral visualization items and Rerun recordings.],
    [Supports debugging while preserving manifests and metrics as the scientific record.],
    [Reporting],
    [Experiment matrix, metric tables, limitations, and method recommendations.],
    [Turns artifact-backed runs into scientific claims after validation.],
    bottomrule(),
  ),
  caption: [Supplementary artifact map for reproducing and extending the benchmark framework.],
) <tab:artifact-map>
