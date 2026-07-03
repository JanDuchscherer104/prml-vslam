= Future Work

#let fw-box(title, body, fill: rgb("fbfcff"), width: auto) = block(
  width: width,
  fill: fill,
  stroke: 0.6pt + fill.darken(25%),
  radius: 5pt,
  inset: (x: 0.45em, y: 0.36em),
)[
  #text(weight: "semibold")[#title]
  #parbreak()
  #body
]

#let fw-arrow = text(size: 9pt)[$arrow.r$]

== COLMAP as an Offline Baseline

One useful next step is a comparison against COLMAP. COLMAP is not a real-time VSLAM system. It is an
offline SfM/MVS pipeline. It first estimates camera poses and sparse points, and then reconstructs a
dense model @schoenberger2016sfm @schoenberger2016mvs. This makes it a good reference baseline for
quality, but not automatic ground truth. Especially our Record3D dataset could be improved substantially by this.
Monocular COLMAP can still have unknown scale and can fail on blurred, texture-poor, or dynamic phone videos.

#figure(
  {
    set text(size: 7.2pt)
    grid(
      columns: (1fr, auto, 1fr, auto, 1fr),
      rows: (auto, auto),
      gutter: 0.28em,
      align: horizon,
      fw-box([Same video frames], [shared sampling and intrinsics], fill: rgb("eef3ff")),
      fw-arrow,
      fw-box([VSLAM branch], [online trajectory and dense cloud], fill: rgb("eef8f3")),
      fw-arrow,
      fw-box([Same metrics], [Sim(3), Chamfer, F-score, runtime], fill: rgb("f7f1ff")),
      [],
      [],
      fw-box([COLMAP branch], [offline SfM poses and MVS cloud], fill: rgb("fff7ec")),
      [],
      [],
    )
  },
  caption: [Future COLMAP comparison: the input frames stay the same, but one branch is online VSLAM and the other is offline SfM/MVS. Both must be evaluated with the same alignment and metric protocol.],
) <fig:future-colmap-baseline>

== Frame Rate and Resolution Sweeps

Another open question is how much quality we lose when we make the input cheaper. We already optimized the parameter for
our runs and tried to stay true to the values which where depicted in their respective papers, but we found several
inconsistencies and improvements for our specific hardware. Lower resolution means fewer pixels and less GPU memory, but it can remove details that tracking or dense prediction
needs. A larger frame stride means fewer frames pass through the model, but the motion gap between two
used frames becomes larger. Future runs should sweep `target_fps`, `frame_stride`, and
`rgb_max_width_px`, and report accuracy, dense-cloud quality, runtime, and failure rate together
@bodin2018slambench2 @sturm2012benchmark. It would be interesting to find direct correlations between those
parameters, and the accuracy/performance of our methods.

#figure(
  {
    set text(size: 7.2pt)
    grid(
      columns: (1fr, 1fr),
      gutter: 0.55em,
      [
        #fw-box([Reduce resolution], [
          #box(width: 2.0cm, height: 0.95cm, fill: rgb("dbe8ff"), stroke: 0.5pt + rgb("8caee8"))
          #h(0.25em) #fw-arrow #h(0.25em)
          #box(width: 1.35cm, height: 0.64cm, fill: rgb("dbe8ff"), stroke: 0.5pt + rgb("8caee8"))
          #parbreak()
          faster and smaller, but less image detail
        ], fill: rgb("eef3ff"), width: 100%)
      ],
      [
        #fw-box([Increase frame stride], [
          #grid(
            columns: (auto, auto, auto, auto, auto, auto),
            gutter: 0.08em,
            box(width: 0.23cm, height: 0.19cm, fill: rgb("4f7dd6"), radius: 2pt),
            box(width: 0.23cm, height: 0.19cm, fill: rgb("d9dee8"), radius: 2pt),
            box(width: 0.23cm, height: 0.19cm, fill: rgb("4f7dd6"), radius: 2pt),
            box(width: 0.23cm, height: 0.19cm, fill: rgb("d9dee8"), radius: 2pt),
            box(width: 0.23cm, height: 0.19cm, fill: rgb("4f7dd6"), radius: 2pt),
            box(width: 0.23cm, height: 0.19cm, fill: rgb("d9dee8"), radius: 2pt),
          )
          #parbreak()
          fewer frames, but larger motion gaps
        ], fill: rgb("eef8f3"), width: 100%)
      ],
    )
  },
  caption: [Resolution and frame-stride sweeps measure the quality/runtime tradeoff instead of assuming one fixed preprocessing setting is best.],
) <fig:future-resolution-stride>

== NKSR and Poisson Surface Reconstruction

The metric pipeline currently evaluates aligned point clouds. The system now integrates Neural Kernel Surface Reconstruction (NKSR) and Poisson surface reconstruction to generate cohesive 3D meshes. The team merged the initial implementation and parameter fine-tuning to establish a foundation for continued work. This configuration processes the dense point cloud outputs from ViSTA-SLAM and produces a final surface mesh.

While the initial parameter tuning is integrated, further optimization and validation remain active areas for future development. These methods require distinct evaluation metrics. A smooth mesh does not always indicate accurate SLAM geometry. Future iterations must refine the reconstruction parameters across diverse datasets and evaluate the resulting mesh geometry against established baselines.

#figure(
  image("../../figures/pointcloud/poisson-reconstruction-final-vista-mesh-orginal-vista-pointcloud-and-trajectory.png", width: 100%),
  caption: [Visual comparison between the original ViSTA-SLAM point cloud, the estimated camera trajectory, and the final mesh generated via Poisson surface reconstruction.],
) <fig:future-poisson-reconstruction>

#figure(
  {
    set text(size: 7.2pt)
    grid(
      columns: (1.05fr, auto, 1.15fr, auto, 1.15fr, auto, 1.15fr),
      gutter: 0.22em,
      align: horizon,
      fw-box([Partial clouds], [frames or pointmaps], fill: rgb("eef3ff")),
      fw-arrow,
      fw-box([Shared frame], [poses, scale, provenance], fill: rgb("eef8f3")),
      fw-arrow,
      fw-box([Reconstruction], [NKSR, Poisson, or 3DGS], fill: rgb("fff7ec")),
      fw-arrow,
      fw-box([Evaluation], [cloud, mesh, and render metrics], fill: rgb("f7f1ff")),
    )
  },
  caption: [Future point-cloud fusion: partial observations are placed in one frame, reconstructed by a declared backend, and then evaluated as geometry or as rendered images.],
) <fig:future-pointcloud-fusion>

== Standardized Metric Clouds

Before reconstruction methods are compared, the input to the metric itself should be standardized.
For example, spatial downsampling before ICP changes which points can become nearest neighbors. The
metric record should therefore store the reference-cloud sampling, voxel size, crop volume, outlier
filter, ICP threshold, inlier statistics, and final metric-cloud pair. This is especially important
for intrinsics-free dense monocular methods such as ViSTA-SLAM, where point density and surface noise
can affect Chamfer distance and F-score independently of the camera trajectory @besl1992method
@zhou2018open3d @zhang2026vistaslam. We should also explore the possibility of runtime pointcloud fusion.
There are scenes, in which geometries are swept several times, creating overlapping pointclouds. Fusing those
overlapping clouds could result in a more accurate reconstruction, and reduces the amount of points that need to be tracked.

#figure(
  {
    set text(size: 7.2pt)
    grid(
      columns: (1fr, auto, 1fr, auto, 1fr, auto, 1fr),
      gutter: 0.22em,
      align: horizon,
      fw-box([Raw clouds], [reference and estimate], fill: rgb("fbfcff")),
      fw-arrow,
      fw-box([Metric clouds], [same voxel size and filters], fill: rgb("eef3ff")),
      fw-arrow,
      fw-box([ICP], [threshold, fitness, RMSE], fill: rgb("eef8f3")),
      fw-arrow,
      fw-box([Scores], [accuracy, Chamfer, F-score], fill: rgb("fff7ec")),
    )
  },
  caption: [Future metric-cloud contract: preprocessing choices become part of the recorded metric, not hidden implementation details.],
) <fig:future-metric-cloud-contract>

== Dynamic-Object Filtering

Our reconstruction target is a static scene. Dynamic objects, like moving cars, people, or animals should therefore be
detected and removed before the final scene reconstruction, since they can corrupt the detected static geometry.
Lift4D might be useful here not because we need full 4D output, but because it models dynamic objects in monocular video and completes regions that
were hidden by those objects @litman2026lift4d @kerbl2023gaussian. In a future pipeline, such a stage
could provide masks for dynamic content and an inferred background behind it. The important caveat is
that this completed background is predicted by a learned prior, so it should be marked separately from
directly observed geometry. This part is essential for usage in real-world scenarios.

#figure(
  image("../../figures/papers/lift4d.jpg", width: 100%),
  caption: [Lift4D as a future-work direction for dynamic-object filtering: detect moving objects, remove them from the static reconstruction input, and predict background regions hidden by those objects.],
) <fig:future-lift4d>
