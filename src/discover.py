"""
Clustering and discovery with UMAP + HDBSCAN.
"""

import numpy as np
import pandas as pd
from pathlib import Path
import argparse
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from umap import UMAP
from hdbscan import HDBSCAN
from sklearn.cluster import DBSCAN

from .dataio import load_config

logger = logging.getLogger(__name__)


def reduce_dimensions(embeddings: np.ndarray, config: Dict) -> np.ndarray:
    """Reduce dimensions with UMAP."""
    umap_config = config.get("umap", {})
    
    reducer = UMAP(
        n_neighbors=umap_config.get("n_neighbors", 15),
        min_dist=umap_config.get("min_dist", 0.1),
        n_components=umap_config.get("n_components", 2),
        metric=umap_config.get("metric", "cosine"),
        random_state=umap_config.get("random_state", 42)
    )
    
    reduced = reducer.fit_transform(embeddings)
    
    logger.info(f"UMAP reduced from {embeddings.shape[1]} to {reduced.shape[1]} dimensions")
    
    return reduced


def cluster_embeddings(reduced: np.ndarray, config: Dict) -> np.ndarray:
    """Cluster with HDBSCAN or DBSCAN."""
    cluster_config = config.get("clustering", {})
    method = cluster_config.get("method", "hdbscan")
    
    if method == "hdbscan":
        hdbscan_config = cluster_config.get("hdbscan", {})
        clusterer = HDBSCAN(
            min_cluster_size=hdbscan_config.get("min_cluster_size", 50),
            min_samples=hdbscan_config.get("min_samples", 10),
            cluster_selection_epsilon=hdbscan_config.get("cluster_selection_epsilon", 0.0),
            metric="euclidean"
        )
    else:
        dbscan_config = cluster_config.get("dbscan", {})
        clusterer = DBSCAN(
            eps=dbscan_config.get("eps", 0.5),
            min_samples=dbscan_config.get("min_samples", 10),
            metric="euclidean"
        )
    
    labels = clusterer.fit_predict(reduced)
    
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    
    logger.info(f"Found {n_clusters} clusters, {n_noise} noise points")
    
    return labels


def generate_cluster_cards(df: pd.DataFrame, windows: np.ndarray,
                          output_dir: Path, config: Dict) -> None:
    """Generate cluster analysis cards."""
    analysis_config = config.get("analysis", {})
    
    if not analysis_config.get("generate_cards", True):
        return
    
    n_exemplars = analysis_config.get("n_exemplars", 5)
    
    # Group by cluster
    for cluster_id in sorted(df["cluster"].unique()):
        if cluster_id == -1:  # Skip noise
            continue
        
        cluster_df = df[df["cluster"] == cluster_id]
        
        if len(cluster_df) < n_exemplars:
            continue
        
        logger.info(f"Generating card for cluster {cluster_id} ({len(cluster_df)} samples)")
        
        # Create figure
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle(f"Cluster {cluster_id} ({len(cluster_df)} samples)")
        
        # Plot exemplar waveforms
        for i in range(min(n_exemplars, len(cluster_df))):
            idx = cluster_df.index[i]
            window = windows[idx]
            
            ax = axes[i // 3, i % 3]
            ax.plot(window)
            ax.set_title(f"Exemplar {i+1}")
            ax.set_xlabel("Time")
            ax.set_ylabel("Value")
        
        plt.tight_layout()
        plt.savefig(output_dir / f"cluster_{cluster_id}_card.png", dpi=150)
        plt.close()


def visualize_clusters(df: pd.DataFrame, output_dir: Path) -> None:
    """Visualize UMAP + clusters."""
    plt.figure(figsize=(12, 8))
    
    scatter = plt.scatter(
        df["umap_1"], df["umap_2"],
        c=df["cluster"], cmap="tab20",
        alpha=0.5, s=10
    )
    
    plt.colorbar(scatter, label="Cluster")
    plt.xlabel("UMAP 1")
    plt.ylabel("UMAP 2")
    plt.title("Cluster Visualization")
    
    plt.tight_layout()
    plt.savefig(output_dir / "umap_clusters.png", dpi=150)
    plt.close()
    
    logger.info("Cluster visualization saved")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    # Load config
    config = load_config(args.config)
    
    # Load embeddings
    embeddings_path = Path(config.get("embeddings_path", "./embeddings/embeddings.parquet"))
    logger.info(f"Loading embeddings from {embeddings_path}")
    
    df = pd.read_parquet(embeddings_path)
    
    # Extract embedding columns
    emb_cols = [c for c in df.columns if c.startswith("emb_")]
    embeddings = df[emb_cols].values
    
    logger.info(f"Loaded {len(embeddings)} embeddings with {embeddings.shape[1]} dimensions")
    
    # Reduce dimensions
    reduced = reduce_dimensions(embeddings, config)
    df["umap_1"] = reduced[:, 0]
    df["umap_2"] = reduced[:, 1]
    
    # Cluster
    labels = cluster_embeddings(reduced, config)
    df["cluster"] = labels
    
    # Save results
    output_dir = Path(config.get("output_dir", "./results"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    clusters_path = output_dir / "clusters.parquet"
    df.to_parquet(clusters_path, index=False)
    logger.info(f"Clusters saved to {clusters_path}")
    
    # Visualize
    visualize_clusters(df, output_dir)
    
    # Cluster statistics
    stats = df.groupby("cluster").size().sort_values(ascending=False)
    logger.info(f"\nCluster sizes:\n{stats}")


if __name__ == "__main__":
    main()
