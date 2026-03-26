= Challenge and Scope

The challenge requires an off-device pipeline that accepts raw smartphone video, handles unknown
intrinsics, and outputs both a high-precision trajectory and a dense 3D point cloud. The evaluation
must compare at least two state-of-the-art methods, include ARCore as a baseline where applicable,
and cover both public and custom datasets.

This repository therefore scopes the project into four major surfaces: method integration, custom
data capture, trajectory evaluation, and dense reconstruction evaluation. Heavy external tools are
kept outside the base Python environment and are treated as documented integrations rather than
vendored code.
