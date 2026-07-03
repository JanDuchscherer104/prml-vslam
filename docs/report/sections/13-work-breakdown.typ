= Work Breakdown

== Report Contributions

All team members collaborated on the final structure and synthesis of the document. The specific section responsibilities are as follows:

- *Valentin Bumeder:* Authored the overarching metrics, trajectory evaluation, experiments and project retrospective sections.
- *Jan Duchscherer:* Authored the related work, benchmark framework, LingBot-Map method, datasets, discussion, conclusion and appendix sections.
- *Lukas Röß:* Authored the introduction, ViSTA-SLAM method, NKSR/Poisson surface reconstruction subsection, performance metrics and work breakdown sections.
- *Christopher Kirschner:* Authored the MASt3R-SLAM method and image quality metrics sections.
- *Florian Beck:* Authored the abstract, point cloud evaluation and future work sections.

== Code Contributions

The software implementation distributed pipeline infrastructure, model adapters and evaluation tooling across the team:

- *Valentin Bumeder:* Managed project organization and issue tracking. Implemented the trajectory evaluation pipeline using the `evo` package, the trajectory alignment and the evaluation sweeper.
- *Jan Duchscherer:* Developed the configurable pipeline framework, Rerun Viewer integration and Streamlit application. Implemented the ARCore baseline and developed the video source integrations, incremental 3D reconstruction and point cloud evaluation.
- *Lukas Röß:* Developed the method integration infrastructure, integrated ViSTA-SLAM, implemented the NKSR/Poisson 3D mesh reconstruction pipeline including parameter fine-tuning and briefly supported video source integrations.
- *Christopher Kirschner:* Adapted the MASt3R-SLAM model for the benchmark and implemented the render-based image-quality evaluation stage, including the point-cloud-to-image projection that renders the reconstruction into image space and the per-frame image-quality metrics.
- *Florian Beck:* Implemented the point cloud evaluation, fixed the sweeper implementation and tuned/executed the final sweep runs.