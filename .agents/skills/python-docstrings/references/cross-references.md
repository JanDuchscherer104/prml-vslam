# Cross-References

Use Sphinx-style roles for internal symbols and markdown links for external
sources.

## Preferred Internal Roles

- `:class:` for classes, configs, datamodels, and typed containers
- `:func:` for free functions
- `:meth:` for methods
- `:mod:` for modules
- `:attr:` for attributes and fields
- `:property:` for important computed properties
- `:data:` for exported constants and module-level values

Examples:

- `Return a :class:\`RunPlan\` built from the validated request.`
- `Translate updates through :func:\`translate_slam_update\`.`
- `See :meth:\`RunService.start_run\` for the entrypoint.`
- `Keep pipeline semantics in :mod:\`prml_vslam.pipeline\`.`
- `The payload is stored in :attr:\`RunSnapshot.slam\`.`
- `Use :property:\`MethodId.display_name\` for UI labels.`
- `Respect :data:\`DEFAULT_MAX_FRAMES_IN_FLIGHT\` when tuning credits.`

## Other Useful Roles

Use these only when they add clarity:

- `:exc:` for exception classes mentioned in prose
- `:paramref:` for referencing a parameter name from a method or function

Examples:

- `Propagate :exc:\`ValueError\` only when the caller can recover from it.`
- `When :paramref:\`build_run_request.method\` changes, update the backend spec.`

## External References

Use markdown links for external material:

- API docs
- research papers
- tutorials
- conceptual references

Examples:

- `See [scikit-learn IsolationForest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html).`
- `The anomaly score follows the [Isolation Forest paper](https://seppe.net/aa/papers/iforest.pdf).`

Do not use Sphinx roles for external targets. Keep external links selective and
relevant.
