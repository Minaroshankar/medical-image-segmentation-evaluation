#!/usr/bin/env python3
"""Binary 3D aorta segmentation evaluator, based on the supplied research protocol."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import SimpleITK as sitk
import surface_distance as sd

METRICS = ["DSC", "NSD_2mm", "HD95_mm", "ASSD_mm", "RVD_percent"]


def read_image(path):
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    return sitk.ReadImage(str(path))


def assert_same_geometry(reference, other, label):
    if reference.GetSize() != other.GetSize():
        raise ValueError(f"{label}: size mismatch: {reference.GetSize()} vs {other.GetSize()}")
    for name, tol in (("Spacing", 1e-5), ("Origin", 0.01), ("Direction", 1e-6)):
        a, b = getattr(reference, f"Get{name}")(), getattr(other, f"Get{name}")()
        if not np.allclose(a, b, atol=tol, rtol=0):
            raise ValueError(f"{label}: {name.lower()} mismatch: {a} vs {b}")


def case_metrics(case_id, gt_path, pred_path, image_path=None, tolerance=2.0):
    gt_img = read_image(gt_path)
    pred_img = read_image(pred_path)
    assert_same_geometry(gt_img, pred_img, f"{case_id} prediction")
    if image_path is not None:
        image_img = read_image(image_path)
        assert_same_geometry(gt_img, image_img, f"{case_id} CTA image")

    gt_raw = sitk.GetArrayFromImage(gt_img)
    pred_raw = sitk.GetArrayFromImage(pred_img)
    if not np.isin(gt_raw, (0, 1)).all():
        raise ValueError(f"{case_id}: Ground truth has labels outside 0/1")
    if not np.isin(pred_raw, (0, 1)).all():
        raise ValueError(f"{case_id}: Prediction has labels outside 0/1")
    gt = gt_raw == 1
    pred = pred_raw == 1
    if not gt.any() or not pred.any():
        raise ValueError(f"{case_id}: empty GT or prediction; metrics not defined under this protocol")

    n_gt = int(np.count_nonzero(gt))
    n_pred = int(np.count_nonzero(pred))
    intersection = int(np.count_nonzero(gt & pred))
    dice = 2.0 * intersection / (n_gt + n_pred)
    spacing_zyx = tuple(reversed(gt_img.GetSpacing()))
    distances = sd.compute_surface_distances(gt, pred, spacing_mm=spacing_zyx)
    nsd = sd.compute_surface_dice_at_tolerance(distances, tolerance_mm=tolerance)
    hd95 = sd.compute_robust_hausdorff(distances, percent=95)
    gt_to_pred, pred_to_gt = sd.compute_average_surface_distance(distances)
    assd = (gt_to_pred + pred_to_gt) / 2.0
    rvd = 100.0 * (n_pred - n_gt) / n_gt
    values = [dice, nsd, hd95, assd, rvd]
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{case_id}: non-finite metric")
    return dict(case_id=case_id, DSC=float(dice), NSD_2mm=float(nsd),
                HD95_mm=float(hd95), ASSD_mm=float(assd),
                RVD_percent=float(rvd), pred_voxels=n_pred, gt_voxels=n_gt)


def file_case_id(path):
    return path.name[:-7] if path.name.endswith('.nii.gz') else path.stem


def matching_files(directory):
    paths = sorted([*directory.glob('*.nii.gz'), *directory.glob('*.nii'), *directory.glob('*.mha'), *directory.glob('*.mhd')])
    matches = {}
    for path in paths:
        key = file_case_id(path)
        if key in matches:
            raise ValueError(f"Duplicate case name '{key}' in {directory}")
        matches[key] = path
    return matches


def summary_frame(df):
    entries = []
    for metric in METRICS:
        s = df[metric]
        entries.append(dict(metric=metric, mean=float(s.mean()), sd=float(s.std(ddof=1)) if len(s) > 1 else None,
                            median=float(s.median()), q25=float(s.quantile(0.25)),
                            q75=float(s.quantile(0.75)), min=float(s.min()), max=float(s.max())))
    return pd.DataFrame(entries)


def main():
    ap = argparse.ArgumentParser(description="Evaluate binary aorta segmentation against ground truth")
    ap.add_argument('--gt', type=Path, required=True, help='GT mask file or folder')
    ap.add_argument('--pred', type=Path, required=True, help='Prediction mask file or folder')
    ap.add_argument('--image', type=Path, help='Optional CTA file (single-case mode only), for geometry QC')
    ap.add_argument('--out', type=Path, required=True, help='New output directory')
    ap.add_argument('--tolerance-mm', type=float, default=2.0)
    ap.add_argument('--case-id', type=str, help='Optional case ID for single-case mode')
    args = ap.parse_args()
    if not np.isfinite(args.tolerance_mm) or args.tolerance_mm < 0:
        ap.error('--tolerance-mm must be finite and non-negative')
    if args.out.exists():
        ap.error(f'Output path already exists; refusing to overwrite: {args.out}')
    if args.gt.is_file() and args.pred.is_file():
        pairs = [(args.case_id or file_case_id(args.gt), args.gt, args.pred, args.image)]
    elif args.gt.is_dir() and args.pred.is_dir():
        if args.image is not None:
            ap.error('--image is supported in single-case mode only')
        gt, pred = matching_files(args.gt), matching_files(args.pred)
        if not gt:
            ap.error('No supported mask files found')
        if gt.keys() != pred.keys():
            ap.error(f'Case IDs do not match. Missing predictions: {sorted(gt.keys() - pred.keys())}; '
                     f'extra predictions: {sorted(pred.keys() - gt.keys())}')
        pairs = [(key, gt[key], pred[key], None) for key in sorted(gt)]
    else:
        ap.error('Supply either two files or two directories')

    results = []
    for index, (case_id, gt_path, pred_path, image_path) in enumerate(pairs, 1):
        result = case_metrics(case_id, gt_path, pred_path, image_path, args.tolerance_mm)
        results.append(result)
        print(f'[{index}/{len(pairs)}] {case_id}: DSC={result["DSC"]:.4f} '
              f'NSD={result["NSD_2mm"]:.4f} HD95={result["HD95_mm"]:.2f}mm '
              f'ASSD={result["ASSD_mm"]:.2f}mm RVD={result["RVD_percent"]:.2f}%')
    df = pd.DataFrame(results)
    summary = summary_frame(df)
    args.out.mkdir(parents=True, exist_ok=False)
    df.to_csv(args.out / 'per_case_metrics.csv', index=False, float_format='%.6f')
    summary.to_csv(args.out / 'summary_metrics.csv', index=False, float_format='%.6f')
    config = {'case_count': len(pairs), 'tolerance_mm': args.tolerance_mm,
              'binary_labels': [0, 1], 'geometry_checked': ['size', 'spacing', 'origin', 'direction'],
              'assd_definition': 'Arithmetic mean of two directional surface averages',
              'rvd_definition': '100*(pred_voxels-gt_voxels)/gt_voxels',
              'spacing_order': 'ZYX for surface_distance',
              'empty_mask_policy': 'Error; no silent substitution'}
    (args.out / 'evaluation_config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    print('\nSUMMARY\n' + summary.to_string(index=False))
    print(f'\nSaved to: {args.out}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
