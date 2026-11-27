#!/usr/bin/env bash
# ==============================================================================
# Master Pipeline Orchestrator — Chanakya Research Commons
# Course: V Sem B.Tech Data Mining & Warehousing, Chanakya University, Bangalore
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

PYTHON_BIN=".venv/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

echo "================================================================================"
echo "CHANAKYA RESEARCH COMMONS — END-TO-END PIPELINE"
echo "Project Root: $PROJECT_ROOT"
echo "Python Interpreter: $PYTHON_BIN"
echo "================================================================================"

echo ""
echo "[Step 1/5] Initializing Database Schemas and Department Seeds..."
$PYTHON_BIN scripts/init_db.py

echo ""
echo "[Step 2/5] Generating Synthetic Academic Dataset (520 Papers, 12,900+ Events)..."
$PYTHON_BIN scripts/generate_synthetic_data.py

echo ""
echo "[Step 3/5] Executing Data Warehouse ETL (Star Schema in DuckDB & Parquet)..."
$PYTHON_BIN analytics/etl_warehouse.py

echo ""
echo "[Step 4/5] Executing Scientific Evaluation Suite (Search, Recs, Spam, Trends, RAG)..."
$PYTHON_BIN evaluation/run_all_evaluations.py

echo ""
echo "[Step 5/5] Running Automated Unit & Integration Tests..."
$PYTHON_BIN tests/test_all_subsystems.py

echo ""
echo "================================================================================"
echo "PIPELINE COMPLETED SUCCESSFULLY!"
echo "All 9 Subsystems, Datasets, Warehouse Cubes, and Benchmarks are Ready."
echo ""
echo "To launch the web platform locally:"
echo "  $PYTHON_BIN -m flask --app app:create_app run --port=5000"
echo "================================================================================"
