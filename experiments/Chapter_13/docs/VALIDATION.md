# Preparation checks and remaining execution

Prepared from the instructor Chapter 13 links and the supplied assignment images.

## Checks performed in the preparation environment

- Python source compiled successfully.
- Both MongoDB JavaScript files passed Node syntax checks.
- All Compose and Kubernetes YAML files parsed successfully.
- Three data services and three StatefulSet replicas confirmed in configuration.
- No MongoDB host ports published; shared key mount and separate data volumes checked.
- Kubernetes ConfigMap script content matched its JavaScript source files.
- Shared Secret, initContainer, serviceName and PVC-template wiring checked.
- MongoDB WiredTiger cache set to 0.3 GB, within the documented allowed bounds.
- Credential generation produced a valid 756-byte random key; rerunning preserved it.
- The Kubernetes key Secret decoded to exactly that same original keyfile.
- A partial credential pair was rejected rather than silently regenerated.
- Report validation rejected missing evidence and invalid authentication, unchanged
  primary, failed Prometheus status, unchanged pod UID and missing publication proof.
- A complete isolated test fixture was accepted; it was used only to test report
  behavior/layout. No fixture result is included as actual lab evidence.
- The six-page preparation PDF and populated report layout were rendered and visually reviewed.

## Not executed here

Docker, Kubernetes, PowerShell and Terraform runtimes are not installed in this
preparation workspace. Therefore no image build/pull, MongoDB deployment, live
failover, Prometheus scrape, pod deletion/recovery, PowerShell execution, Terraform
validate/plan/apply, or Docker Hub publication is claimed to have passed here.

Your local scripts collect those real results. If any step fails, stop at that step
and send its error text. The final report remains unavailable until required measured
lab results and publication proof exist. The preparation PDF must not be submitted
as a completed-lab report.

## Version scope

MongoDB uses the 7.0 image series from the teaching reference; its patch can advance.
The runner uses Python 3.12 with pinned Python dependencies. Prometheus is pinned to
v3.0.1. Terraform constrains the Atlas provider to v2; terraform init records the
selected version in the local lockfile. The publication script records the actual
submission-image digest after push/pull.

## Bootstrap correction after the first Windows run

The user confirmed the Docker runner built and all three MongoDB containers became
healthy, but mongosh threw code 94 before initiation. Bootstrap now catches only
NotYetInitialized (code 94) and continues with initiation. Other errors propagate.
Four simulated JavaScript regression cases passed: numeric code 94, the error name,
an already-authenticated deployment, and rejection of an unexpected authorization
error. The Kubernetes ConfigMap contains the same corrected script. A live rerun
is still required to verify the remaining lab steps.

## Mongosh compatibility correction, repair V2

The user encountered TypeError: assert.commandWorked is not a function. All
uses of shell assertion helpers were replaced with ordinary JavaScript checks in
bootstrap.js and k8s-check.js, including write concern/write error checks.
Authentication checks accept successful boolean, numeric or ok responses.
The previous NotYetInitialized catch remains. Scripts use explicit --file flags.
Twelve simulated cases passed with NO assert global available, including a partially
initialized set, existing users, authorization failures and Kubernetes write/data
failures. This catches the unavailable-helper defect missed by the earlier test
stub. These are simulations, not live Docker or Kubernetes execution.
The full tests are in tests/mongosh-scripts.test.cjs; run with Node.js if desired.
FIX_MONGOSH.ps1 updates both scripts and the ConfigMap without changing credentials
or volumes. The older FIX_BOOTSTRAP.ps1 download has also been updated.

## Interactive publication login correction

The first publish attempt passed all evidence checks, then failed with password
required. PUBLISH.ps1 now invokes docker login directly so prompts are visible,
using Docker Hub browser/device-code sign-in when needed. It checks the login exit
code before building/pushing and asks for a student name rather than accepting the
Docker username as the report author. This change was inspected statically; browser
authentication and publication must still be completed on the user's machine.
