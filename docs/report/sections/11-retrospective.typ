#import "@preview/booktabs:0.0.4": bottomrule, midrule, toprule

= Retrospective

This section reflects on the practical impact of the project's tooling and infrastructure choices,
distinguishing what worked well from what caused avoidable friction.

== What went right?

AI coding agents were used throughout the project to improve development speed and to build the
first pipeline setup. This produced a fast proof-of-concept containing a Streamlit application for
interactive visualization and Rerun as an artifact viewer, and let the team iterate on the
architecture quickly instead of hand-writing scaffolding.

The early architectural decision to define standardized boundaries between pipeline stages paid off
beyond the initial setup. It allowed the team to work on multiple stages in parallel instead of creating
hard dependencies on previous stages. This kept the focus on a fully configurable pipeline that
eased integrating and running different VSLAM methods. On top of this foundation, multiple datasets
were supported, a live streaming mode was implemented using Record3D, and a sweeper utility was
built to execute many runs during the benchmarking phase. This enabled the benchmarking of different methods, producing the
baseline data for the metrics evaluation.

== What went wrong?

The same AI-assisted speed that accelerated the early setup also made it easy to introduce features
that were not critical to the project's success. As a result, the pipeline's scope grew beyond what
was originally planned, which led to large refactoring efforts and time-consuming debugging during
the project's finalization phase.

Development was also constrained by the available hardware. Method parameters had to be strongly
reduced to fit within the memory limits of the GPUs used for development, which does not necessarily
reflect each method's intended operating configuration. Several bugs and misconfigurations were only
discovered late in the project, once runs were finally executed at a larger scale. Evaluating the
metrics from the initial sweeper run revealed that the configuration contained incorrect parameters,
which led to non-representative results. Fine-tuning the parameters and rerunning the sweeps cost
valuable time that had been planned for a deeper evaluation of the metrics.
