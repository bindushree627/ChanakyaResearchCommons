"""
Scholarly Paper Duplicate Detection Evaluation Suite.
Evaluates algorithmic duplicate detection against planted ground truth pairs.
Calculates Precision, Recall, and F1-Score.
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import Config
from mining.duplicate_detection.paper_dedup import detect_all_duplicates

GROUND_TRUTH_FILE = Config.SYNTHETIC_DATA_DIR / "ground_truth_duplicates.json"

def evaluate_duplicates(threshold=0.85):
    print("=" * 60)
    print("Evaluating Duplicate Paper Detection against Planted Ground Truth")
    print("=" * 60)

    if not GROUND_TRUTH_FILE.exists():
        raise FileNotFoundError(f"Planted duplicate ground truth not found: {GROUND_TRUTH_FILE}")

    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
        ground_truth_list = json.load(f)

    # Ground truth pairs as normalized set of tuples
    gt_pairs = set()
    for item in ground_truth_list:
        p1 = item["original_id"]
        p2 = item["duplicate_id"]
        pair = (min(p1, p2), max(p1, p2))
        gt_pairs.add(pair)

    # Run detection
    detected = detect_all_duplicates(threshold=threshold)
    detected_pairs = set()
    for d in detected:
        p1 = d["paper_a_id"]
        p2 = d["paper_b_id"]
        pair = (min(p1, p2), max(p1, p2))
        detected_pairs.add(pair)

    # Compute confusion matrix metrics
    true_positives = len(detected_pairs & gt_pairs)
    false_positives = len(detected_pairs - gt_pairs)
    false_negatives = len(gt_pairs - detected_pairs)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    print(f"Ground Truth Planted Duplicates: {len(gt_pairs)}")
    print(f"Algorithmically Detected Pairs: {len(detected_pairs)}")
    print(f"True Positives: {true_positives} | False Positives: {false_positives} | False Negatives: {false_negatives}")
    print(f"Precision: {precision:.4f} | Recall: {recall:.4f} | F1-Score: {f1:.4f}")

    return {
        "GroundTruthCount": len(gt_pairs),
        "DetectedCount": len(detected_pairs),
        "TruePositives": true_positives,
        "FalsePositives": false_positives,
        "FalseNegatives": false_negatives,
        "Precision": round(precision, 4),
        "Recall": round(recall, 4),
        "F1_Score": round(f1, 4)
    }

if __name__ == "__main__":
    evaluate_duplicates()
