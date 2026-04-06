# Questions Q&A 26.03.2026

- Do we need to deliver a **real-time streaming** pipeline?

    > Yes, Real time uncalibrated VSLAM should be used on a video stream from emergency calls such that the operator can be presented with a streaming SLAM and (optionally) 3DGS scene reconstruction, so that they can instruct the caller and get a better understanding of the scene. The only available modality consists of the video stream for now. A top down view (BEV) might also be a helpful modality to the operator.

- Can we get access to the **GPU cluster** for inference and potential fine-tuning?

    > Yes, it's also possible to get compute resources via LRZ.

- Why develop **own app**? **Only capture or also display?** Or can we display in Streamlit?

    > The project's long term goal consits of the reconstruction being displayed for the operator, so the smartphone serves only as capture device. However it would be helpful for the user to see relevant information that might help them on the screen (not important for this project).

- In custom dataset, what should be used as **GT Trajectory**?

    > Capturing our own offline dataset is necessary, however, we can use apps like Record3D. iPhones provide calibrated RGB-D frames, otherwise traditional (non-realtime) SLAM (i.e. SfM methods) need to be used to provide a target.

- What role is ARCore supposed to play in our project?

    > ARCore is optional in this project. Treat it as an explicit external baseline when it helps with comparison or bootstrapping, not as a required part of the primary monocular VSLAM pipeline.

- Can we use a **synthetic dataset**?

    > Yes, possible, but why. Why? Flexibility, high quality GT.

- Priority of the eval spaces (i.e. Trajectory > PC > Dense recon > 3DGS recon)


- What Role does 3DGS and hence maybe Nerfstudio play for our project?

    > As, described eaerlier, a great endproduct would be a system where the uncalibrated RGB stream feeds the creation of a 3DGS scene representation, so that the Operator can assume  _couterfactual_ SE(3) poses to get a better scene understanding so that they can give spatial guidance to the caller.
