= Metrics

Trajectory evaluation should quantify both global and local behavior. Core examples are alignment
error, pose drift, and sequence-level consistency. The exact metric suite should remain stable
across methods and be reported in a reproducible scriptable form.

Dense reconstruction evaluation should quantify geometric fidelity, completeness, and failure modes
such as missing structure or noisy surfaces. Open3D @zhou2018open3d and comparable point-cloud tooling
can provide a practical baseline for alignment and metric computation.
