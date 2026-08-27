# Evently — Form intake service

A minimal REST API for creating forms and collecting submissions, built as a
Cloud & DevOps assignment. The weight of the work is in the container image,
the local environment and the CI/CD pipeline rather than in the application.

## Prerequisites

Docker. Nothing else, no Python and no `uv` installation is required to run
the project.

## Quick start

```bash
docker compose up --build
```

The API is then available on <http://localhost:8000>, with interactive
documentation at <http://localhost:8000/docs>.

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0","environment":"local"}
```

Stop with `Ctrl+C`, then `docker compose down`.

### Development mode

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

This overlay mounts `./app` read-only into the container and runs uvicorn with
`--reload`, so code changes take effect without rebuilding the image. It also
sets `EVENTLY_ENVIRONMENT=dev`, which `/health` reports back, so it is visible
which variant is running.

The overlay is deliberately **not** named `docker-compose.override.yml`: that
filename loads automatically, which would make the development variant the
default. Here the default is the production-shaped container and development is
opted into.

### Without Docker

```bash
uv sync
uv run uvicorn app.main:app --reload
uv run pytest -q
```

## API

| Method | Path                        | Description                     |
| ------ | --------------------------- | ------------------------------- |
| GET    | `/health`                   | Health check, version and environment |
| POST   | `/forms`                    | Create a form                   |
| POST   | `/forms/{id}/submissions`   | Submit an entry to a form       |
| GET    | `/forms/{id}/submissions`   | List a form's submissions       |

```bash
# Create a form
curl -X POST http://localhost:8000/forms \
  -H "Content-Type: application/json" \
  -d '{"title": "Friday borrel", "description": "Drinks at the office"}'

# Submit to it (use the id returned above)
curl -X POST http://localhost:8000/forms/<id>/submissions \
  -H "Content-Type: application/json" \
  -d '{"data": {"name": "Jane", "attending": true}}'

# Read the submissions back
curl http://localhost:8000/forms/<id>/submissions
```

A malformed id returns `422` (rejected before reaching application code); a
well-formed id that does not exist returns `404`.

## Structure

```
app/
  main.py      application factory
  config.py    typed settings, read from EVENTLY_* environment variables
  api.py       endpoints
  models.py    request and response models
  store.py     in-memory storage, isolated behind one class
tests/         integration tests against the four endpoints
Dockerfile     multi-stage build
docker-compose.yml, docker-compose.dev.yml
.github/workflows/ci.yml
```

## Key decisions

**Python 3.12 with FastAPI.** The application is four endpoints in any
language, so the stack was chosen to leave maximum time for the DevOps layer.
FastAPI derives validation and OpenAPI documentation from type hints, which is
code that does not have to be written or maintained.

**uv with a committed lockfile.** `uv.lock` pins every direct and transitive
dependency, and `uv sync --frozen` is used in both the image build and CI, so a
stale lockfile fails the build instead of silently resolving a different
dependency tree. `.python-version` pins the interpreter for the same reason.

**Multi-stage Dockerfile.** The builder stage produces a virtualenv; the runtime
stage starts from a clean base and copies only that virtualenv plus the source.
Left behind: the `uv` binary, its download cache and all development tooling
(`--no-dev`). Measured result: **242 MB vs 634 MB** on disk, **57.7 MB vs
154 MB** to pull, against a naive single-stage build.

**`python:3.12-slim-bookworm`, not Alpine.** Alpine uses musl rather than
glibc, so PyPI's prebuilt wheels do not apply and a missing wheel means
compiling from source mid-build. Predictable builds were preferred over a
smaller base.

**Non-root runtime.** A dedicated system user with a fixed uid, so a
compromised process does not start as root inside the container.

**Dependencies installed before source is copied.** The dependency layer is
keyed on the lockfile alone, so a code change does not reinstall packages.

**Two CI jobs, not one and not six.** `quality` (lint, type check, tests) and
`image` (build, smoke test, scan, publish) with `needs: quality`, so an image is
never built or published from code that failed its tests. Six jobs would each
pay for their own runner and checkout, for a test suite that runs in under a
second.

**Trivy gates on fixable findings only.** The scan reports every severity for
visibility, but fails the build only on `HIGH`/`CRITICAL` findings that have a
fix available. The current image reports 222 findings, all Debian base-layer
CVEs with no upstream patch; gating on those would leave the pipeline
permanently red for reasons nothing in this repository can resolve, and a
permanently red pipeline gets ignored. Application dependencies scan clean.

**Published to GHCR, from `main` only.** Authentication uses the built-in
`GITHUB_TOKEN`, so no secret has to be created or shared and the pipeline works
for anyone who forks the repository. Images are tagged with both the short
commit SHA and `latest`. Pull requests run the identical checks but publish
nothing.

## Assumptions

- Submissions are arbitrary key/value payloads. Forms do not declare their
  fields, so submitted data is not validated against a schema.
- Storage is in-memory and process-local: data does not survive a restart and
  does not span replicas. This is the boundary of "in-memory storage is fine",
  not an oversight, see next steps.
- No authentication or authorisation. Every endpoint is public.
- No lock is needed around the store because every endpoint is `async def` and
  therefore runs on a single event loop; no dictionary operation contains an
  `await`, so none can be interrupted half-finished. Writing an endpoint as a
  plain `def` would run it in a threadpool and break that guarantee.
- The healthcheck is defined in compose rather than in the Dockerfile. The
  runtime image has no `curl`, and in a real deployment the platform performs
  the probe; the image's job is to expose `/health` and answer it.

## CI/CD pipeline

Triggered on pushes to `main`, pull requests targeting `main`, and manually via
`workflow_dispatch`. Runs are grouped per branch with `cancel-in-progress`, so
pushing twice in quick succession cancels the superseded run.

1. **quality.** Installs dependencies with a cached `uv`, then runs `ruff`,
   `mypy` and `pytest`.
2. **image.** Builds the image with Buildx layer caching, starts it and polls
   `/health` until it answers (a build succeeding does not prove the image
   runs), scans it with Trivy, and on `main` pushes it to GHCR.

The image is built once and loaded locally, so the scan and smoke test run
against the exact artefact that gets published.

### Running this elsewhere

No secrets or manual setup are required beyond the repository setting
**Settings → Actions → General → Workflow permissions → Read and write**, which
allows the built-in token to push to GHCR. On GitLab the equivalent would be a
two-stage `.gitlab-ci.yml` using the built-in `CI_REGISTRY` variables, with the
same job ordering.

## Next steps

Deliberately left out of scope, in rough priority order:

- **Persistent storage.** Replace `InMemoryStore` with Postgres behind the same
  interface, making the service stateless and horizontally scalable. Nothing
  outside `store.py` changes.
- **Field-level validation.** Let forms declare their fields and validate
  submissions against them, instead of accepting arbitrary payloads.
- **Deploy to a real target.** Add a deployment stage to Azure Container Apps or
  Fly.io, gated on a successful publish, with the environment supplied through
  the existing `EVENTLY_*` variables.
- **Distroless base image.** Would remove the shell and package manager from the
  runtime image and cut the base-layer CVE count substantially. The concrete
  case: `pip` ships in the base image with 5 findings and is never used at
  runtime; it could be stripped or avoided entirely.
- **Pin GitHub Actions to commit SHAs.** Version tags are mutable, the Trivy
  action's own tags were migrated after a supply-chain incident. SHA pinning
  removes that risk at the cost of readability.
- **Pin the base image by digest** rather than tag, so builds are reproducible
  down to the exact base.
- **Sign published images** (cosign) so a deployed tag can be verified.
- **Authentication** on the write endpoints, and rate limiting on submissions.
- **Structured JSON logging** with request ids, and metrics for a real
  observability stack.
- **Automate action updates.** Several GitHub Actions are a major version
  behind; Dependabot or Renovate would keep them current. Related: `setup-uv`
  now ships immutable full-version tags only, which is the same supply-chain
  reasoning behind SHA pinning above.
