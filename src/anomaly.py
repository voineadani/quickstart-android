"""
Anomaly detection using reconstruction error, isolation forest, and centroid distance.
"""

import numpy as np
import pandas as pd
from pathlib import Path
import argparse
import logging
from sklearn.ensemble import IsolationForest
from typing import Dict

from .dataio import load_config

logger = logging.getLogger(__name__)


def compute_reconstruction_error(embeddings: np.ndarray, 
                                reconstructions: np.ndarray) -> np.ndarray:
    """Compute MAE reconstruction error."""
    errors = np.mean(np.abs(embeddings - reconstructions), axis=1)
    return errors


def compute_isolation_forest_scores(embeddings: np.ndarray,
                                   contamination: float = 0.1) -> np.ndarray:
    """Compute anomaly scores using Isolation Forest."""
    iso_forest = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_jobs=-1
    )
    
    scores = iso_forest.fit_predict(embeddings)
    # Convert to anomaly score (higher = more anomalous)
    decision_scores = -iso_forest.score_samples(embeddings)
    
    return decision_scores


def compute_centroid_distance(embeddings: np.ndarray,
                             cluster_labels: np.ndarray) -> np.ndarray:
    """Compute distance to cluster centroid."""
    distances = np.zeros(len(embeddings))
    
    for cluster_id in np.unique(cluster_labels):
        if cluster_id == -1:  # Noise
            continue
        
        mask = cluster_labels == cluster_id
        cluster_embs = embeddings[mask]
        
        # Compute centroid
        centroid = cluster_embs.mean(axis=0)
        
        # Distance to centroid
        dists = np.linalg.norm(cluster_embs - centroid, axis=1)
        distances[mask] = dists
    
    # Noise points get max distance
    distances[cluster_labels == -1] = distances.max() if distances.max() > 0 else 1.0
    
    return distances


def normalize_scores(scores: np.ndarray) -> np.ndarray:
    """Normalize scores to [0, 1]."""
    min_score = scores.min()
    max_score = scores.max()
    
    if max_score - min_score < 1e-10:
        return np.zeros_like(scores)
    
    return (scores - min_score) / (max_score - min_score)


def detect_anomalies(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    """Detect anomalies using ensemble of methods."""
    df = df.copy()
    
    # Extract embeddings
    emb_cols = [c for c in df.columns if c.startswith("emb_")]
    embeddings = df[emb_cols].values
    
    logger.info(f"Detecting anomalies in {len(embeddings)} samples...")
    
    # Method 1: Isolation Forest
    iso_scores = compute_isolation_forest_scores(embeddings)
    iso_scores_norm = normalize_scores(iso_scores)
    df["anomaly_score_isolation"] = iso_scores_norm
    
    # Method 2: Centroid distance (if clusters available)
    if "cluster" in df.columns:
        centroid_dists = compute_centroid_distance(embeddings, df["cluster"].values)
        centroid_dists_norm = normalize_scores(centroid_dists)
        df["anomaly_score_centroid"] = centroid_dists_norm
    else:
        df["anomaly_score_centroid"] = 0.0
    
    # Ensemble anomaly score (max-normalized sum)
    df["anomaly_score"] = (
        df["anomaly_score_isolation"] + 
        df["anomaly_score_centroid"]
    ) / 2
    
    # Flag top anomalies
    threshold = df["anomaly_score"].quantile(0.95)
    df["is_anomaly"] = df["anomaly_score"] > threshold
    
    n_anomalies = df["is_anomaly"].sum()
    logger.info(f"Detected {n_anomalies} anomalies ({n_anomalies/len(df)*100:.2f}%)")
    
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    # Load config
    config = load_config(args.config)
    
    # Load clusters
    clusters_path = Path(config.get("clusters_path", "./results/clusters.parquet"))
    logger.info(f"Loading clusters from {clusters_path}")
    
    df = pd.read_parquet(clusters_path)
    
    # Detect anomalies
    df = detect_anomalies(df, config)
    
    # Save results
    output_dir = Path(config.get("output_dir", "./results"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    anomalies_path = output_dir / "anomalies.csv"
    anomaly_df = df[df["is_anomaly"]].copy()
    anomaly_df.to_csv(anomalies_path, index=False)
    
    logger.info(f"Anomalies saved to {anomalies_path}")
    logger.info(f"Top 10 anomaly scores:\n{df.nlargest(10, 'anomaly_score')[['window_id', 'anomaly_score']]}")


if __name__ == "__main__":
    main()
