# 3D Medical Image Segmentation Evaluation

A lightweight, model-independent Python tool for evaluating **3D binary medical image segmentation** against ground-truth annotations.

Originally developed for abdominal aorta segmentation in CT angiography (CTA), this tool can also be used to evaluate other binary 3D segmentation tasks.

It supports single-case and batch evaluation, physical geometry validation, and reproducible CSV reporting.

## Features

- Five segmentation evaluation metrics
- Single-case and batch evaluation
- Support for NIfTI and MetaImage formats
- Image geometry and binary label validation
- Optional reference image for additional geometry checks
- Configurable NSD tolerance
- Per-case and summary statistics
- Custom case IDs for single-case evaluation
- No model weights or GPU required

## Evaluation Metrics

| Metric | Description | Interpretation |
|---|---|---|
| DSC | Dice Similarity Coefficient | Higher is better |
| NSD | Normalized Surface Dice at 2 mm tolerance | Higher is better |
| HD95 | 95th-percentile robust Hausdorff distance (mm) | Lower is better |
| ASSD | Average Symmetric Surface Distance (mm) | Lower is better |
| RVD | Signed Relative Volume Difference (%) | Closer to zero is better |

DSC and NSD range from 0 to 1, with 1 indicating perfect agreement under their respective definitions.

Signed RVD distinguishes over-segmentation (positive values) from under-segmentation (negative values).

ASSD is calculated as the arithmetic mean of the two directional average surface distances.

## Requirements

- Python 3.11 or a compatible Python version
- NumPy
- Pandas
- SimpleITK
- surface-distance 0.1

Install the required dependencies:

```bash
python -m pip install -r requirements.txt
```

The PyPI package `surface-distance` is imported in Python as `surface_distance`.

## Usage

### 1. Single-Case Evaluation

Provide a ground-truth mask and a predicted segmentation mask:

```bash
python evaluate_segmentation.py \
  --gt GT_mask.nii.gz \
  --pred Pred_mask.nii.gz \
  --case-id patient001 \
  --out results_patient001
```

The `--case-id` argument is optional and allows a custom identifier to be assigned to the case.

Without this argument, the case ID is derived from the ground-truth filename.

### 2. Single-Case Evaluation with Reference Image

An optional CTA image can be supplied for geometry validation:

```bash
python evaluate_segmentation.py \
  --image CTA.nii.gz \
  --gt GT_mask.nii.gz \
  --pred Pred_mask.nii.gz \
  --case-id patient001 \
  --out results_patient001
```

The reference image is used only to verify spatial geometry. Segmentation metrics are calculated from the predicted and ground-truth masks.

### 3. Batch Evaluation

Organize ground-truth masks and predictions into separate directories:

```text
dataset/
├── ground_truth/
│   ├── patient001.nii.gz
│   ├── patient002.nii.gz
│   └── patient003.nii.gz
└── predictions/
    ├── patient001.nii.gz
    ├── patient002.nii.gz
    └── patient003.nii.gz
```

Run:

```bash
python evaluate_segmentation.py \
  --gt dataset/ground_truth \
  --pred dataset/predictions \
  --out results_batch
```

Files are matched using identical basenames after removing supported image extensions.

Supported formats:

- `.nii.gz`
- `.nii`
- `.mha`
- `.mhd`

Different supported extensions may be used for a matching ground-truth and prediction pair.

### 4. Custom NSD Tolerance

The default NSD tolerance is 2 mm. To change it:

```bash
python evaluate_segmentation.py \
  --gt GT_mask.nii.gz \
  --pred Pred_mask.nii.gz \
  --tolerance-mm 1.0 \
  --out results_custom
```

## Outputs

Each evaluation creates three files:

| File | Contents |
|---|---|
| `per_case_metrics.csv` | Five metrics and foreground voxel counts for each case |
| `summary_metrics.csv` | Mean, sample standard deviation, median, quartiles, minimum and maximum |
| `evaluation_config.json` | Evaluation parameters and methodological definitions |

The script refuses to overwrite an existing output directory.

For single-case evaluations, the sample standard deviation is undefined and is recorded as a missing value.

## Quality Control

Before computing metrics, the tool verifies:

- Matching image dimensions
- Voxel spacing consistency
- Image origin consistency
- Image direction consistency
- Binary segmentation labels (0 and 1)
- Non-empty ground-truth and prediction masks
- Finite evaluation results

Images must already be aligned on the same physical grid. The tool does not perform automatic registration or resampling.

## Numerical Validation

The evaluation methodology was validated against archived results from a pretrained abdominal aorta segmentation baseline.

**Validation date:** October 31, 2026

| Validation item | Result |
|---|---|
| Test cases | 33/33 |
| Compared metric values | 165/165 |
| Metrics per case | 5 |
| Maximum absolute difference between stored CSV values | 0.0 |
| Comparison precision | Six decimal places |

All 165 stored metric values reproduced the archived evaluation results at six-decimal precision.

The comparison was performed using the original project-local `surface_distance` dependency on the SimorghPC research server.

A subsequent single-case test of the updated script also confirmed correct metric reproduction and custom case ID assignment.

These results establish numerical consistency with the archived reference implementation. An independent fresh-install test has not yet been performed.

No patient images or ground-truth masks are included in this repository.

## Methodological Considerations

- Evaluation is intended for binary segmentation.
- Both ground-truth and prediction masks must contain only labels 0 and 1.
- Empty masks produce an error rather than silently assigning arbitrary metric values.
- Surface-distance calculations use array axis order ZYX, with voxel spacing converted from SimpleITK's XYZ order.
- Surface distances are expressed in millimetres.
- Oblique or non-orthogonal image grids may require additional validation of the physical-distance assumptions.
- The reference CTA image is optional and is used for geometry checking only.
- This tool evaluates existing predictions; it does not perform segmentation inference or model training.

## Intended Applications

This tool is designed for researchers and engineers working with:

- Abdominal aorta segmentation
- Medical image segmentation benchmarking
- Deep learning segmentation model comparisons
- Binary volumetric segmentation evaluation
- Reproducible segmentation experiments

## Data Privacy

This repository contains evaluation code only. No patient imaging data, ground-truth annotations, model weights, or identifiable clinical records are distributed.

## License

No open-source license is currently specified. Reuse and redistribution permissions remain reserved until an appropriate license is selected.
