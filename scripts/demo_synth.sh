#!/bin/bash
# Quick demo with synthetic data

set -e

echo "=== Quick Demo with Synthetic Data ==="
echo

echo "Generating synthetic driving data..."
python -m synthetic.generator --output ./data/demo_trip.csv --n_trips 3

echo
echo "Demo complete! Data saved to ./data/"
echo "Run './scripts/run_all.sh' to process the data"
