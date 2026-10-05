# tensor_qtl_cis

Nominal cis tensorQTL mapping for Terra managed Cromwell, using WDL 1.0.
The source is the supplied `tensorqtl_cis_nominal_v1-0_BETA_modified.1.wdl`.

## Runtime

Uses the same GPU runtime as `AoU-Multiomics-Analysis/tensorQTL_trans`:
`g2-standard-16`, NVIDIA L4, `us-central1-c`, and the existing
`gcr.io/broad-cga-francois-gtex/tensorqtl:latest` image.
Use `num_gpus=1`, `num_threads=16`, and `memory=64` (GB) for this machine.
The GPU count defaults to one. Disk size and preemptible retries remain inputs.
The existing image uses a mutable tag; this change does not build a new image.

## Inputs and outputs

Input keys retain the prefix
`tensorqtl_cis_nominal_workflow.tensorqtl_cis_nominal.`:

- Required files: `plink_pgen`, `plink_pvar`, `plink_psam`, `phenotype_bed`, `covariates`.
- Optional files: `interaction`, `phenotype_groups`.
- Required settings: `prefix`, `memory`, `disk_space`, `num_threads`, `num_preempt`.
- Optional setting: `num_gpus` (default 1).

All input files remain typed Files until command rendering. The task checks
localized paths and links the PLINK files to a common basename, even when Terra
places them in different directories. Optional flags are passed only when their
files are supplied. The prefix must start with a letter or digit and contain
only letters, digits, dots, underscores, or hyphens.

The task and workflow expose `chr_parquet` and `log`. The supplied workflow's
nominal cis mode and analysis options are preserved.

## Validation

GitHub Actions checks WDL syntax, GPU settings, the rendered command, optional
files, safe path quoting, and rejection of unresolved cloud URIs. An AST check
rejects workflow-scope file-writing functions. A CPU smoke test runs the actual
tensorQTL engine on generated PLINK2 data and checks a known association.
No local Docker build is required.

CPU and command tests do not validate GPU execution, the production image, or
Terra localization. The complete workflow has not been tested on Terra.
