# Ray Runtime Patterns

Use this reference when implementing or reviewing Ray-hosted pipeline
runtimes, `StageRuntimeProxy`, runtime sidecars, transient payload handling, or
same-LAN Ray deployment behavior.

This note is a navigation aid. Verify detailed API behavior against the
official Ray docs before implementing non-trivial runtime behavior.

## Official Docs Entry Points

- [Actors](https://docs.ray.io/en/latest/ray-core/actors.html)
- [Actor task execution order](https://docs.ray.io/en/latest/ray-core/actors/task-orders.html)
- [Objects](https://docs.ray.io/en/latest/ray-core/objects.html)
- [Resources](https://docs.ray.io/en/latest/ray-core/scheduling/resources.html)
- [Runtime environments](https://docs.ray.io/en/latest/ray-core/handling-dependencies.html)
- [Actor termination](https://docs.ray.io/en/latest/ray-core/actors/terminating-actors.html)
- [Actor fault tolerance](https://docs.ray.io/en/latest/ray-core/fault_tolerance/actors.html)
- [State CLI/API](https://docs.ray.io/en/latest/ray-observability/reference/cli.html)
- [Custom metrics](https://docs.ray.io/en/latest/ray-observability/user-guides/add-app-metrics.html)

## Runtime Proxy Boundary

- Keep raw Ray actor handles, task refs, object refs, and `.remote()` calls
  inside `StageRuntimeProxy`, `RuntimeManager`, or Ray helper modules.
- `StageRunner`, coordinator, app, and CLI code should call runtime protocol
  methods and receive `StageResult`, `StageRuntimeUpdate`, and
  `StageRuntimeStatus` values, not Ray-specific objects.
- Track submitted, completed, failed, and in-flight method calls in the proxy
  when Ray-hosting a runtime. Surface those counters through
  `StageRuntimeStatus`.

## Actor Ordering And Streaming Commands

- Ray actor method ordering is a deployment property, not the public pipeline
  queue contract.
- `submit_stream_item(...)` is an ingress command; it should not return
  semantic updates.
- `drain_runtime_updates(...)` is the observation query; it should return
  updates already produced by completed or observed runtime work.
- Do not expose Ray mailbox depth as portable pipeline telemetry.

## Object References And Transient Payloads

- Ray `ObjectRef`s are substrate-owned references. Do not put them in public
  pipeline DTOs.
- Public live payload metadata is `TransientPayloadRef`. Runtime-side payload
  stores and resolvers map those refs to concrete Ray objects, local arrays, or
  other substrate-owned payloads.
- Use typed not-found behavior for read-after-eviction instead of leaking Ray
  errors or object-store details.

## Placement, Resources, And Runtime Environments

- Translate pipeline resource policy into Ray options only in the Ray backend
  or runtime layer.
- Keep CPU, GPU, memory, custom resources, node labels/IP hints, and runtime
  environment selection substrate-neutral in pipeline config.
- Expose stable Ray initialization policy such as `log_to_driver` and
  `include_dashboard` through repo-owned runtime config instead of hard-coded
  `ray.init(...)` kwargs.
- Keep private or unstable Ray init flags, such as `_skip_env_hook`, internal
  to the backend/runtime layer unless the project commits to a public contract
  for them.
- Treat current Ray retry knobs as implementation details until the project has
  a repo-level retry policy.

## Stop, Failure, And Observability

- On stop or failure, stop accepting new stream submissions before draining or
  finalizing active runtime work.
- Prefer graceful finish/stop paths; reserve immediate actor kill for timeout
  or unrecoverable runtime failure.
- Use Ray State API and Dashboard data for diagnostics, not canonical pipeline
  state.
- Use Ray custom metrics for runtime-owned counters when useful, while keeping
  `StageRuntimeStatus` as the pipeline contract.
