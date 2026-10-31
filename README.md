# Binary Aorta Segmentation Evaluation

Evaluates 3D binary masks: **DSC**, **NSD (2 mm)**, **HD95 (mm)**, **ASSD (mm)** and **signed RVD (%)**.

## Install

```bash
python -m pip install -r requirements.txt
```

The PyPI package is `surface-distance`, imported as `surface_distance`.

## Single case (CTA image optional; used for geometry checking, not metric calculation)

```bash
python evaluate_segmentation.py --image CTA.nii.gz --gt GT_mask.nii.gz --pred Pred_mask.nii.gz --out results_case
```

## Batch mode

Ground-truth and prediction folders must contain **identically named files** (e.g. `case001.nii.gz` in both). Supported extensions: `.nii.gz`, `.nii`, `.mha`, `.mhd`.

```bash
python evaluate_segmentation.py --gt ground_truth --pred predictions --out results_batch
```

## Outputs

- `per_case_metrics.csv`: each case and its five metrics
- `summary_metrics.csv`: mean, sample SD, median, quartiles, min/max for each metric
- `evaluation_config.json`: settings and definitions

## Important methodological notes

- Both masks must contain **only 0 and 1**. In this protocol empty GT or prediction masks cause a clear error; no arbitrary metric values are assigned.
- Size, spacing, origin and direction are verified between masks; the optional CTA is used *only* to verify matching geometry.
- `surface_distance` uses array order **ZYX**. Spacing is therefore reversed from SimpleITK's XYZ order.
- ASSD is the arithmetic mean of the two directional average surface distances; RVD is signed.
- Predictions and ground truth must be on the same physical grid, without requiring any resampling by this tool. Oblique/non-orthogonal physical grids require additional validation of surface-distance assumptions.
- **Numerical validation (31 Oct 2026):** 33/33 test cases and 165/165 stored metric values matched the original Model 1 pretrained-baseline evaluation CSV to six decimal places (maximum absolute CSV difference = 0.0). The original 33-case comparison was run on the SimorghPC server with the project-local `surface_distance` dependency. Independent fresh-install validation and the single-case filename fix in this final package remain to be re-tested before official delivery.
- Single-case `case_id` is derived from the ground-truth filename without `.nii.gz`, `.nii`, `.mha`, or `.mhd`; suffixes like `_mask` are retained.
- Batch file matching is based on exact basenames without extensions, so matching `case001.nii.gz` and `case001.mha` is supported.
- The script refuses to overwrite an existing output directory.
