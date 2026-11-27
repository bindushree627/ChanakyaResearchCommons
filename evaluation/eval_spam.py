"""
Spam & Anomaly Detection Evaluation Suite.
Evaluates Isolation Forest and behavioral heuristic rules against planted spam accounts.
Outputs Confusion Matrix (TP, FP, TN, FN), Precision, Recall, and F1-Score.
"""

import json
from pathlib import Path
from app.config import Config
from app.models.db import query_db
from mining.anomaly_detection.spam_detector import detect_spam_accounts

GROUND_TRUTH_FILE = Config.SYNTHETIC_DATA_DIR / "ground_truth_spam_users.json"

def evaluate_spam_detection():
    print("=" * 60)
    print("Evaluating Spam & Abuse Detection against Planted Bot Accounts")
    print("=" * 60)

    if not GROUND_TRUTH_FILE.exists():
        raise FileNotFoundError(f"Planted spam ground truth file not found: {GROUND_TRUTH_FILE}")

    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
        ground_truth_spam = json.load(f)

    gt_spam_uids = {s["user_id"] for s in ground_truth_spam}
    all_users = query_db("SELECT id FROM users")
    all_uids = {u["id"] for u in all_users}
    gt_legit_uids = all_uids - gt_spam_uids

    # Run detection
    detected = detect_spam_accounts()
    detected_uids = {d["user_id"] for d in detected}

    # Confusion matrix
    tp = len(detected_uids & gt_spam_uids)
    fp = len(detected_uids & gt_legit_uids)
    fn = len(gt_spam_uids - detected_uids)
    tn = len(gt_legit_uids - detected_uids)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / len(all_uids) if all_uids else 0.0

    print(f"Total Users: {len(all_uids)} | Planted Spam Accounts: {len(gt_spam_uids)}")
    print(f"Confusion Matrix: TP={tp}, FP={fp}, FN={fn}, TN={tn}")
    print(f"Precision: {precision:.4f} | Recall: {recall:.4f} | F1-Score: {f1:.4f} | Accuracy: {accuracy:.4f}")

    return {
        "TotalUsers": len(all_uids),
        "PlantedSpam": len(gt_spam_uids),
        "ConfusionMatrix": {
            "TruePositives": tp,
            "FalsePositives": fp,
            "FalseNegatives": fn,
            "TrueNegatives": tn
        },
        "Precision": round(precision, 4),
        "Recall": round(recall, 4),
        "F1_Score": round(f1, 4),
        "Accuracy": round(accuracy, 4)
    }

if __name__ == "__main__":
    evaluate_spam_detection()
