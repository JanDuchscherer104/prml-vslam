= Work Breakdown

== Report Contributions

All team members collaborated on the final structure and synthesis of the document. The specific section responsibilities are as follows:

- *Valentin Bumeder:* Authored the overarching metrics, trajectory evaluation, experiments and project retrospective sections.
- *Jan Duchscherer:* Authored the related work, benchmark framework, LingBot-Map method, datasets, discussion, conclusion and appendix sections.
- *Lukas Röß:* Authored the introduction, ViSTA-SLAM method, performance metrics and work breakdown sections.
- *Christopher Kirschner:* Authored the MASt3R-SLAM method and image quality metrics sections.
- *Florian Beck:* Authored the abstract, point cloud evaluation and future work sections.

== Code Contributions

The software implementation distributed pipeline infrastructure, model adapters and evaluation tooling across the team:

- *Valentin Bumeder:* Managed project organization and issue tracking. Implemented the trajectory evaluation pipeline using the `evo` package, the trajectory alignment and the evaluation sweeper.
- *Jan Duchscherer:* Developed the configurable pipeline framework, Rerun Viewer integration and Streamlit application. Implemented all three datasets and iPhone live streaming, recorded the custom dataset, implemented RANSAC ground-plan detection and ICP point cloud alignment, as well as the LingBot-Map adapter.
- *Lukas Röß:* Developed the method integration infrastructure, integrated ViSTA-SLAM, implemented the NKSR/Poisson 3D mesh reconstruction and briefly supported video source integrations.
- *Christopher Kirschner:* Adapted the MASt3R-SLAM model for the benchmark and implemented output-image quality metrics.
- *Florian Beck:* Implemented the point cloud evaluation and fixed the sweeper implementation.
