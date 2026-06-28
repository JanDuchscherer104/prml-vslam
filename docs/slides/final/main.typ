#import "../template.typ": *
#import "../update-meetings/_shared/team.typ": team_entry

#let team_members = [
  Jan Duchscherer, Lukas Röß, Christopher Kirschner, \ Valentin Bumeder, Florian Beck
]

#let footer_members = [
  J. Duchscherer, V. Bumeder, L. Röß, C. Kirschner, F. Beck
]

#let compact_note(body) = block(
  fill: rgb("f4f6fb"),
  inset: (x: 0.7em, y: 0.55em),
  radius: 6pt,
  stroke: 0.6pt + rgb("d9dee8"),
)[#body]

#show: definitely-not-isec-theme.with(
  aspect-ratio: "16-9",
  slide-alignment: top,
  progress-bar: true,
  // font: "Noto Sans",
  institute: [Munich University of Applied Sciences, Department of Computer Science & Mathematics],
  logo: [#image("../../figures/hm-logo.svg", width: 2cm)],
  config-info(
    title: [Uncalibrated Monocular VSLAM],
    subtitle: [Final presentation],
    authors: team_members,
    extra: [
      Pattern Recognition & Machine Learning
    ],
    footer: [#project_footer(
      footer_authors: footer_members,
      footer_label: [PRML VSLAM],
      footer_date: [#datetime(year: 2026, month: 7, day: 02).display("[day padding:none]. [month repr:short] [year]")],
    )],
    download-qr: "",
  ),
  config-common(handout: false),
  config-colors(
    primary: theme_color_primary_hm,
    lite: theme_color_block,
  ),
)

#set text(size: 18pt)

#show figure.caption: set text(size: 12pt, weight: "medium", fill: theme_color_footer.darken(40%))
#show link: set text(fill: blue)
#show link: it => underline(it)
#show ref: set text(size: 12pt)

#title-slide()

#slide(title: [Team])[
  #align(center + horizon)[
    #team_entry
  ]
]

#slide(title: [Motivation: Uncalibrated Monocular VSLAM])[
  - Domain Introduction & Goals
  - _LUKAS_
]

// TODO: maybe one slide per method?
#slide(title: [Method Comparison])[
  - conceptual comparison of the three candidate methods (ViSTA, MASt3R, LingBot)
  - What are their main distinctive features?
  #grid(
    columns: (1fr, 1fr, 1fr),
    [
      *MASt3R* @murai2025mast3rslam:\
      _Christopher_
      - *Foundation Model Prior:* heavy pre-trained network → robust 3D geometry "in-the-wild".
      - *Direct 3D Matching:* matches in 3D ray-space, not 2D features.
      - *Generic Camera:* handles changing intrinsics mid-video (e.g. zoom).
      - Output: camera path + dense colored cloud → input for our metrics.
    ],
    [
      *ViSTA*:\
      - no priviledged reference frame,
      - traditional SLAM backend
      _Lukas_
    ],
    [
      *LingBot*:\
      - end-to-end learning-based SLAM,
      - Geometric Context Transformer
      _Jan_
    ],
  )
]

#section-slide(title: [Methodology & Results], subtitle: [Interesting Implementation Details])

#slide(title: [JD])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.75cm,
    [
      *Seed material, not final ownership*

      - Standardized stage boundaries.
      - Pipeline framework and artifact contracts.
      - Source normalization for ADVIO, TUM RGB-D, Record3D.
      - Sim(3), gravity-aware alignment, ICP.
    ],
    [
      #quote-block[
        #lorem(5)
      ]
    ],
  )
]

// #slide(title: [Pipeline Framework])[
//   #grid(
//     columns: (1.05fr, 0.95fr),
//     [
//       - `RunConfig` compiles into a deterministic `RunPlan`.
//       - Runtime order: `source -> slam -> gravity.align -> evaluate.trajectory -> reconstruction -> evaluate.cloud -> summary`.
//       - `StageResult` is the typed terminal handoff.
//       - `StageRuntimeUpdate` carries live telemetry and neutral visualization items.
//       #good-note[Run artifacts, manifests, and summaries are the reproducibility contract.]
//     ],
//     [
//       #figure(
//         image("../../figures/mermaid/pipeline/03-run-config-stage-plan.png", height: 75%),
//         caption: [`RunConfig` to stage plan.],
//       )
//     ],
//   )
// ]

// ===========================================================================
// Valentin Bumeder — Trajectory Evaluation
// ===========================================================================
#slide(title: [Trajectory Evaluation — The Alignment Problem])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.8cm,
    [
      *A monocular camera cannot observe:*
      - the *scale*,
      - the *world frame* (translation),
      - the *orientation* (rotation).

      → Estimate and reference are *never* in the same frame,
      scale, or orientation.

      → Alignment of *estimate onto the reference*

      #note[
        *Pipeline:*
        - associate by timestamp (≤ 10 ms) → $"Sim"(3)$ align → measure.
        - No alignment ⇒ no metric.
      ]
    ],
    [
      *Sim(3) alignment (Umeyama @umeyama1991least):*
      best-fit *slide + spin + resize*.

      $ bold(S)^* = arg min_(bold(S) in "Sim"(3)) sum_i norm(bold(x)_i^"ref" - bold(S) bold(x)_i^"est")^2 $
      $ bold(S) bold(x) = underbrace(s, "scale") underbrace(bold(R), "rot.") bold(x) + underbrace(bold(t), "transl.") $

      - Recovered scale $s$ is *itself a result*: $s approx 1$ ⇒ metric
        scale recovered.

      #good-note[
        *ADVIO (phone, near-planar):* lock $bold(R)$ to *yaw about
        gravity* — full $"Sim"(3)$ could flip a flat path upside-down.
      ]
    ],
  )
]

#slide(title: [Trajectory Evaluation — Metrics: APE & RPE])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.8cm,
    [
      *Two questions × two quantities (m / deg):*

      #table(
        columns: (auto, 1fr),
        align: (left, left),
        inset: (x: 0.4em, y: 0.4em),
        table.header([], [*translation* / *rotation*]),
        [*APE* (global)], [_is the whole map right?_],
        [*RPE* (local)], [_is each step right?_],
      )

      $ bold(e)_i^"APE" = op("trans")(bold(T)_i^(-1) hat(bold(T))_i) $
      $ bold(E)_i^"RPE" = (bold(T)_i^(-1) bold(T)_(i+h))^(-1) (hat(bold(T))_i^(-1) hat(bold(T))_(i+h)) $

      #text(size: 13pt)[Headline = *RMSE* over all residuals;
      $Delta = 1"m"$ for RPE @grupp2017evo.]
    ],
    [
      *Interpretation* — the reason we report both:

      - *Low RPE + High APE* → good local tracking, *global
        drift* (weak/no loop closure).
      - *High RPE* → noisy, locally inconsistent odometry.
      - *APE* catches drift & loop-closure quality;
        *RPE* is robust to a single big error.
    ],
  )
]

#slide(title: [Trajectory Evaluation — First Results (pilot sweep)])[
  #set text(size: 14pt)
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.7cm,
    [
      *Completion:* #h(0.3em)
      ViSTA *18/18*, MASt3R *9/18*.

      #warning-note[
        *All 6 ADVIO MASt3R runs failed* (+ Record3D 27-25, TUM
        floor/room) in the `align.trajectory` stage.
      ]

      *Why MASt3R fails — a chain:*
      + `max_frames = 50` (vs ViSTA's 512).
      + accepts only *1–5 keyframes* of those 50 (ViSTA: 138–417).
      + writes *1 trajectory pose per keyframe*.
      + $≤ 2$ poses ⇒ fails the $"Sim"(3)$ *spread check*.

      #text(size: 12pt)[Config-driven *and* a real robustness weakness:
      keyframing is intolerant of sparse/fast sampling.]
    ],
    [
      #figure(
        table(
          columns: 5,
          align: (left, center, center, center, center),
          inset: (x: 0.35em, y: 0.34em),
          table.header(
            [Dataset], [APEt ViSTA], [done], [APEt MASt3R], [done],
          ),
          [TUM f1 (×6)], [≈0.10 m], [6/6], [≈0.03 m], [4/6],
          [Record3D (×6)], [≈0.46 m], [6/6], [≈0.03 m], [5/6],
          [ADVIO (×6)], [≈1.95 m], [6/6], [—], [0/6],
        ),
        caption: [Mean APE-translation RMSE; "done" = runs with metrics.],
      )

      - *Scale recovery:* MASt3R $s approx 1.0$ (metric model) vs
        ViSTA $s = 0.4 dots 11$ (scale-free).
      - MASt3R's tiny APE rests on *3–5 pairs* (7-DoF fit ⇒
        near-overfit) and has *no RPE at all*.

      #note[
        *Caveats:* ADVIO is hard for both (ViSTA APE-rot 80–170°,
        under investigation); LingBot pending; full 50×3 matrix is
        future work.
      ]
    ],
  )
]

#slide(title: [Point Cloud Evaluation])[
  - ICP: Iterative Closest Point
  - Metrics used.
  -
]

// ===========================================================================
// Christopher Kirschner — MASt3R
// ===========================================================================
#slide(title: [Render-based Image Metrics])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.8cm,
    [
      *Idea:* Evaluate *in image space*.

      - Render the dense cloud from the *estimated poses* (Open3D
        projection @zhou2018open3d).
      - Compare each render to the nearest input frame, *pixel-wise*.
      - Score only *filled* pixels (mask $Omega$) — don't punish the
        cloud for holes it never covered.
    ],
    [
      *Metrics* — over the $N$ filled pixels $Omega$ ($I$ real, $hat(I)$ render):

      $ "L1" = 1/N sum_(p in Omega) abs(I_p - hat(I)_p) $
      #text(size: 13pt)[→ mean per-pixel error.]

      $ "PSNR" = 10 log_10 (L^2 \/ "MSE") $
      #text(size: 13pt)[→ higher = closer. MSE = mean sq. error, $L$ = max value (255).]

      - SSIM: local *structure*, 7×7 window @wang2004ssim.
      - Coverage: fraction of pixels the cloud fills.

      #note[
        Read every score *with coverage* — the absolute number means
        little on its own.
      ]
    ],
  )
]

#slide(title: [Results — what they say])[
  #grid(
    columns: (1.15fr, 0.85fr),
    gutter: 0.7cm,
    [
      #figure(
        table(
          columns: 6,
          align: (left, center, center, center, center, center, center),
          table.header(
            [Method], [Pairs], [Cov.], [PSNR], [SSIM], [L1],
          ),
          [ViSTA-SLAM], [357], [0.79], [10.8], [0.10], [0.19],
          [MASt3R-SLAM], [154], [0.63], [11.2], [0.07], [0.18],
        ),
        caption: [
          Render-based image-quality results on ADVIO
          advio-15 @cortes2018advio. PSNR/SSIM/L1 averaged over filled
          pixels.
        ],
      )

      *Takeaways:*
      - *Not an absolute quality score* — we use these to *compare the two
        methods* on the same sequence.
      - *Low SSIM could mean a sparse cloud, not bad geometry:* SSIM's sliding
        window also feels the holes, while PSNR/L1 mask pixels cleanly.
    ],
    [
      #figure(
        image("../../figures/render_eval/vista_advio15_sbs_a.png", width: 100%),
        caption: [
          Ground truth (left) vs. ViSTA's dense cloud rendered from the
          estimated camera pose (right).
        ],
      )
    ],
  )
]

#slide(title: [Real-time Performances])[

  - FPS + latency?
  - own measurments and paper reported numbers.
  - nvidia-smi and perf stats.
]


#slide(title: [Future Work])[
  // Flo
  - Strong FPS dependence of ViSTA and MASt3R (limitation for streaming when FPS is low).
  - Real-time capability on consumer grade GPUs with loss of performance.
  -
]

#slide(title: [Retrospective: What went right, what went wrong?])[
  // Valentin
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.8cm,
    [
      #good-note(width: 100%)[#align(center)[*What went right* ✓]]

      - *AI* enabled a quick project setup (pipeline, Streamlit app, Rerun).
      - Pipeline made integrating *multiple SLAM methods* easy
        (ViSTA, MASt3R, LingBot).
      - Supports *multiple datasets* (ADVIO, TUM, Record3D).
      - *Fully configurable:* method, source, VSLAM config (frames…),
        evaluation steps.
      - *Sweeper* runs all sources × all methods.
    ],
    [
      #warning-note(width: 100%)[#align(center)[*What went wrong* ✗]]

      - Fast POC — but *huge refactorings* from AI slop.
      - *Slow, intensive finalization:* running evaluation &
        getting comparable results across methods.
      - Hard to find the *best-fit parameters per method*.
      - First sweep had a *misconfiguration* — MASt3R/ViSTA config mismatch messed up the results.
    ],
  )
]

#slide(title: [References])[
  #set text(size: 9pt)
  #set par(leading: 0.75em, spacing: 0.18em)
  #set list(spacing: 0.18em)
  #show list.item: it => block(breakable: false)[it]
  #columns(2, gutter: 0.9cm)[
    #bibliography("../../references.bib", title: none)
  ]
]
