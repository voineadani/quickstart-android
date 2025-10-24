#!/bin/bash
# Complete pipeline execution script

set -e  # Exit on error

echo "=== iDrive Behavior Analysis Pipeline ==="
echo

# Check if data exists, otherwise generate synthetic data
if [ ! -d "./data" ] || [ -z "$(ls -A ./data)" ]; then
    echo "No data found. Generating synthetic data..."
    python -m synthetic.generator --output ./data/synthetic_trip.csv --n_trips 5
fi

echo "Step 1: Training SSL model (TNC)..."
python -m src.ssl_train --config ./configs/train_ssl.yml --method tnc

echo
echo "Step 2: Extracting embeddings..."
python -m src.embed --config ./configs/train_ssl.yml --ckpt ./ckpts/tnc_final.pt --method tnc

echo
echo "Step 3: Clustering..."
python -m src.discover --config ./configs/cluster.yml

echo
echo "Step 4: Generating weak labels..."
python -m src.weaklabels --config ./configs/weaklabels.yml

echo
echo "Step 5: Detecting anomalies..."
python -m src.anomaly --config ./configs/cluster.yml

echo
echo "=== Pipeline Complete ==="
echo "Results saved to ./results/"
echo "Embeddings saved to ./embeddings/"
echo "Model checkpoints saved to ./ckpts/"
