= From VSLAM to 3D Gaussian Splatting

#let challenge_intro_link_blue = rgb("#2563eb")
#show link: set text(fill: challenge_intro_link_blue)

Among the recent papers relevant to this project, MASt3R-SLAM is the single most useful anchor for
planning how an uncalibrated monocular benchmark should proceed because it explains how a modern
two-view 3D prior can be turned into a real-time dense SLAM pipeline under a generic central camera
assumption @murai2025mast3rslam. DROID-SLAM is the clearest optimization reference for dense
bundle-adjustment-style reasoning in learned SLAM @teed2021droidslam, ViSTA-SLAM sharpens the
uncalibrated and Sim(3)-aware perspective that is especially relevant for smartphone video with
unknown intrinsics @zhang2026vistaslam, and 3D Gaussian Splatting defines the downstream scene
representation that becomes interesting only after camera motion and coarse geometry are stable
@kerbl2023gaussiansplatting. This section therefore treats MASt3R-SLAM as the narrative spine,
uses ViSTA-SLAM and DROID-SLAM to explain the geometry and optimization choices, and ends with
3D Gaussian Splatting as the natural dense scene representation for operator-facing rendering and
inspection.#footnote[
  For quick intuition on the classical background, useful entry points are
  #link("https://en.wikipedia.org/wiki/Bundle_adjustment")[bundle adjustment],
  #link("https://en.wikipedia.org/wiki/Structure_from_motion")[structure from motion],
  #link("https://en.wikipedia.org/wiki/Projective_geometry")[projective geometry], and
  #link("https://en.wikipedia.org/wiki/Simultaneous_localization_and_mapping")[simultaneous
  localization and mapping].
]

== Why This Bridge Matters

The challenge in this repository is not only to estimate a trajectory from monocular video, but to
recover geometry that is sufficiently stable to support dense inspection, comparison against
reference reconstructions, and potentially a downstream radiance-field representation. These goals
are related, but they are not identical. A method can achieve low trajectory error while still
producing noisy or incomplete geometry, and a renderer can produce visually plausible views while
hiding errors in scale, drift, or structure. The most useful reading strategy is therefore to
separate the problem into three layers: geometric inference from images, global consistency of
camera poses and local geometry, and conversion of the recovered scene into a rendering-oriented
representation.

Classical multiple-view geometry provides the common language for the first layer
@hartley2003multiple. Its basic imaging relation can be written as

$
lambda_(i,j) x_(i,j) = K_i [R_i | t_i] X_j,
$

where $x_(i,j)$ is an image measurement in
#link("https://en.wikipedia.org/wiki/Homogeneous_coordinates")[homogeneous coordinates], $X_j$ is
a scene point, $[R_i | t_i]$ is the camera pose, $K_i$ is the intrinsic calibration, and
$lambda_(i,j)$ is the unknown projective depth. This equation matters because it separates the
observable image ray from the hidden metric structure of the scene. Once many such correspondences
are available, the canonical global objective is
#link("https://en.wikipedia.org/wiki/Bundle_adjustment")[bundle adjustment], which jointly
optimizes structure and motion @triggs2000bundleadjustment:

$
E_b = sum_((i, j) in O) rho(e_(i,j)^t e_(i,j)),
quad
e_(i,j) = pi(K_i, T_i X_j) - u_(i,j).
$

This objective states that the correct reconstruction is the one whose projected 3D structure best
explains the image measurements after a robust loss $rho$ suppresses outliers. In a calibrated
pipeline, the projection function $pi$ is explicit and the geometry is naturally expressed in pixel
space. In the present challenge, however, the smartphone intrinsics are unknown, may vary across
devices, and may be unreliable under strong distortion. That makes it dangerous to treat the
calibrated pixel-space objective as the only truth criterion. The most important conceptual shift in
the recent monocular dense SLAM literature is therefore not the abandonment of geometry, but the
replacement of brittle handcrafted frontends by learned two-view 3D priors and more flexible
residual definitions.

== Dense Monocular SLAM Under Unknown Intrinsics

DROID-SLAM shows why dense optimization remains the right conceptual template even in learned
systems @teed2021droidslam. Its key idea is to iteratively update camera poses and dense inverse
depth while a differentiable dense bundle-adjustment layer enforces global agreement between current
geometry and revised correspondences. This is important for the present report because it explains
why long trajectories cannot be handled reliably by local pairwise matching alone: the front-end may
propose correspondences, but consistency over many frames still has to be solved as a structured
optimization problem.

MASt3R-SLAM keeps the same global-consistency principle, but changes the front-end representation
and the camera assumptions in a way that is much better aligned with the current challenge
@murai2025mast3rslam. Instead of assuming a fixed parametric camera model at the front-end, it
starts from a two-view 3D reconstruction prior that predicts pointmaps and matching features, and it
reasons under a generic central camera assumption. The practical consequence is that the method can
operate before exact calibration is known. In this setting, a ray-space residual is often more
appropriate than a pure pixel-space reprojection residual because the direction of a ray is usually
more reliable than its absolute depth when calibration and scale are uncertain. A generic form of
such an objective is

$
E_r = sum_((m, n) in M_(i,j)) rho(r_(m,n)^t r_(m,n)),
quad
r_(m,n) = d(X_(i,m)) - d(T_(i,j) X_(j,n)).
$

The direction map $d(.)$ normalizes a 3D point prediction into a viewing direction through the
camera center. Conceptually, this objective says that two matched scene predictions should agree in
angle even if metric depth is still uncertain. This is one of the most useful theoretical ideas for
an uncalibrated smartphone benchmark because it clarifies why the project should keep calibrated and
uncalibrated execution branches explicit instead of hiding them behind a single score table.

ViSTA-SLAM complements this perspective by showing that the uncalibrated monocular problem benefits
from both a lightweight two-view frontend and a backend defined over
#link("https://en.wikipedia.org/wiki/Similarity_(geometry)")[similarity transforms]
@zhang2026vistaslam. In the monocular case, the scale of local predictions can drift even when
relative orientation is accurate. A Sim(3) pose graph models this directly:

$
E_s = sum_((i, j) in E) r_(i,j)^t Omega_(i,j) r_(i,j),
quad
r_(i,j) = log(Delta_(i,j)^(-1) S_i^(-1) S_j).
$

Here $S_i$ is the pose of node $i$ in the similarity group, $Delta_(i,j)$ is the measured relative
constraint between nodes, and $Omega_(i,j)$ weights how strongly that constraint should be trusted.
This equation explains why loop closure is not an optional engineering detail: it is the mechanism
that converts many local two-view estimates into a globally consistent trajectory and map. For this
repository, the implication is clear. The benchmark should always preserve enough intermediate
artifacts to distinguish front-end pairwise quality, local tracking stability, and back-end global
consistency, because each of these can fail for different reasons.

== From Trajectory and Pointmaps to 3D Gaussian Splatting

Once trajectory and coarse geometry are stable, the problem changes. The goal is no longer only to
estimate motion, but to represent the scene in a form that supports dense visualization, view
interpolation, and potentially operator-guided scene understanding. This is where 3D Gaussian
Splatting becomes relevant @kerbl2023gaussiansplatting. The original paper is important because it
does not start from raw video alone. It starts from images, calibrated cameras, and a sparse
#link("https://colmap.github.io/tutorial.html")[structure-from-motion point cloud], and then
optimizes an explicit set of
#link("https://en.wikipedia.org/wiki/Multivariate_normal_distribution")[anisotropic Gaussians]. In
other words, the 3DGS paper already assumes that camera geometry has been solved to a useful
degree. That is exactly why 3DGS should be treated as a downstream stage in this project rather
than as the first benchmark target.

The core primitive in 3DGS is a Gaussian centered at mean $mu$ with covariance $Sigma$:

$
G(x) = exp(-1/2 x^T Sigma^(-1) x),
quad
Sigma = R S S^T R^T.
$

The second expression parameterizes the covariance through a rotation $R$ and scaling matrix $S$,
which guarantees a positive semidefinite covariance and makes the shape of the Gaussian easier to
optimize. The scene is therefore represented as a cloud of oriented ellipsoids rather than as a
voxel grid or an implicit neural field alone. To render these primitives, the 3D covariance is
projected into image space:

$
Sigma' = J W Sigma W^T J^T.
$

The viewing transform $W$ maps the Gaussian into camera coordinates and $J$ is the Jacobian of the
local projective mapping. This equation explains why accurate camera poses remain essential even
after the representation has changed. If the camera geometry is wrong, the projected Gaussian
footprints are wrong, and the renderer will optimize appearance around a geometrically inconsistent
scene.

Rendering then proceeds by front-to-back alpha compositing:

$
C(p) = sum_(i in N(p)) c_i alpha_i product_(j=1)^(i-1) (1 - alpha_j),
$

where $N(p)$ is the ordered set of Gaussians contributing to pixel $p$, $c_i$ is the color or
view-dependent appearance of Gaussian $i$, and $alpha_i$ is its opacity contribution at that pixel.
The conceptual payoff is that 3DGS keeps the image-formation logic of
#link("https://en.wikipedia.org/wiki/Volume_rendering")[volumetric rendering] while replacing
expensive #link("https://en.wikipedia.org/wiki/Ray_marching")[ray marching] with a GPU-friendly
splatting procedure whose per-pixel accumulation still follows
#link("https://en.wikipedia.org/wiki/Alpha_compositing")[alpha compositing]. For this challenge,
the main consequence is methodological rather than merely representational. A 3DGS stage should
consume the best available camera poses and sparse geometry, not attempt to solve the entire
uncalibrated SLAM problem from scratch.

Nerfstudio makes this downstream boundary concrete rather than merely conceptual
@tancik2023nerfstudio.#footnote[
  Useful Nerfstudio entry points are the
  #link("https://docs.nerf.studio/quickstart/custom_dataset.html")[custom dataset guide],
  #link("https://docs.nerf.studio/quickstart/data_conventions.html")[data conventions],
  #link("https://docs.nerf.studio/nerfology/methods/nerfacto.html")[Nerfacto method page],
  and #link("https://docs.nerf.studio/nerfology/methods/splat.html")[Splatfacto method page].
] Its documented custom-data path assumes that camera poses are known for each image and that the
scene has been converted into Nerfstudio's format either through
#link("https://docs.nerf.studio/quickstart/custom_dataset.html")[`ns-process-data`] or through an
explicit #link("https://docs.nerf.studio/quickstart/data_conventions.html")[`transforms.json`] or
#link("https://docs.nerf.studio/developer_guides/pipelines/dataparsers.html")[custom dataparser]
path. Its default #link("https://docs.nerf.studio/nerfology/methods/nerfacto.html")[`nerfacto`]
model is positioned for real captures of static scenes, while
#link("https://docs.nerf.studio/nerfology/methods/splat.html")[`splatfacto`] provides a practical
Gaussian-splatting pipeline together with
#link("https://docs.nerf.studio/quickstart/viewer_quickstart.html")[viewer] and
#link("https://docs.nerf.studio/quickstart/export_geometry.html")[export] tooling. For the present
project, this is valuable in a very specific way: Nerfstudio is a strong candidate for the
downstream radiance-field or 3DGS stage once trajectories, intrinsics, and coarse geometry are
stable, but it should not be confused with the primary uncalibrated VSLAM frontend. It also
sharpens an implementation detail that the report should keep explicit. Nerfstudio documents an
#link("https://docs.nerf.studio/quickstart/data_conventions.html")[OpenGL/Blender-style camera
convention], whereas many SLAM and SfM pipelines expose
#link("https://colmap.github.io/cameras.html")[COLMAP]-style or OpenCV-style cameras, so the
normalization boundary in this repository must preserve frame-convention metadata instead of
assuming that all camera transforms are directly interchangeable.

== Design Recommendations for This Project

The most defensible project plan is to benchmark trajectory recovery and dense geometry recovery
before treating 3DGS as an output metric of its own. MASt3R-SLAM should be the main conceptual paper
for the report because it explains how a two-view 3D prior can drive tracking, local fusion, loop
closure, and global optimization under a weak camera assumption @murai2025mast3rslam. ViSTA-SLAM
should remain the strongest complementary benchmark because it is directly targeted at the
uncalibrated monocular case and makes the Sim(3) story explicit @zhang2026vistaslam. DROID-SLAM
should be cited as the optimization contrast that makes clear why dense iterative refinement and
bundle-adjustment-style backends remain central even when the frontend is learned
@teed2021droidslam.

The implementation consequence is that the pipeline should be staged. First, the project should run
an uncalibrated or weakly calibrated dense SLAM backend to estimate trajectories, keyframes, and
coarse geometry. Second, these outputs should be normalized into a repo-owned artifact contract with
explicit frame conventions, units, timestamps, intrinsics, and calibration assumptions. Third, only
the best trajectory, intrinsics, and geometry products should be passed to a downstream 3DGS or
Nerfstudio stage. This is scientifically cleaner than an end-to-end evaluation because it preserves
diagnostic power. If trajectory quality is poor, the failure should be attributed to SLAM. If trajectory quality is good
but the rendered scene is poor, the failure should be attributed to the radiance-field stage or its
initialization.

Finally, the report should present calibrated and uncalibrated paths as two related but distinct
problem settings. The calibrated path is closer to classical bundle adjustment and to the original
3DGS initialization assumptions. The uncalibrated path is closer to the core challenge and is better
explained through central-camera reasoning, pointmaps, ray-space residuals, and Sim(3) graphs.
Keeping both branches explicit will make later design decisions easier: streaming evaluation can
prioritize trajectory stability and online map quality, while batch evaluation can prioritize global
consistency and the quality of the initialization passed into 3DGS. Useful primary and project-page
links for continuing this line of work include the MASt3R-SLAM paper and repository, the ViSTA-SLAM
paper and repository, the DROID-SLAM paper, and the 3D Gaussian Splatting paper and project
page.#footnote[
  Primary sources:
  #link("https://arxiv.org/abs/2412.12392")[MASt3R-SLAM paper],
  #link("https://github.com/rmurai0610/MASt3R-SLAM")[MASt3R-SLAM repository],
  #link("https://arxiv.org/abs/2509.01584")[ViSTA-SLAM paper],
  #link("https://github.com/zhangganlin/vista-slam")[ViSTA-SLAM repository],
  #link("https://arxiv.org/abs/2108.10869")[DROID-SLAM paper],
  #link("https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/")[3D Gaussian Splatting project page],
  and #link("https://arxiv.org/abs/2308.04079")[3D Gaussian Splatting paper].
]
