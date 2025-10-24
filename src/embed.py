"""
Embedding extraction and export.
"""

import torch
import numpy as np
import pandas as pd
from pathlib import Path
import argparse
import logging
from tqdm import tqdm

from .dataio import load_config, DataLoader as DataIOLoader
from .preprocessing import Preprocessor
from .segmentation import Segmenter
from .models import TNCEncoder, MAETimeSeries, BYOLTimeSeries

logger = logging.getLogger(__name__)


def extract_embeddings(model: torch.nn.Module, windows: np.ndarray,
                      metadata: pd.DataFrame, device: str,
                      batch_size: int = 128) -> pd.DataFrame:
    """Extract embeddings from windows."""
    model.eval()
    
    embeddings = []
    
    with torch.no_grad():
        for i in tqdm(range(0, len(windows), batch_size), desc="Extracting embeddings"):
            batch = windows[i:i+batch_size]
            batch_tensor = torch.from_numpy(batch).float().to(device)
            
            # Get embeddings
            emb = model.get_embedding(batch_tensor)
            embeddings.append(emb.cpu().numpy())
    
    embeddings = np.concatenate(embeddings, axis=0)
    
    # Create dataframe
    emb_cols = [f"emb_{i}" for i in range(embeddings.shape[1])]
    emb_df = pd.DataFrame(embeddings, columns=emb_cols)
    
    # Combine with metadata
    result_df = pd.concat([metadata.reset_index(drop=True), emb_df], axis=1)
    
    return result_df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--ckpt", type=str, required=True)
    parser.add_argument("--method", type=str, choices=["tnc", "mae", "byol"], default="tnc")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    # Load config
    config = load_config(args.config)
    dataset_config = load_config(config["dataset_config"])
    
    # Set device
    device = config["training"].get("device", "auto")
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")
    
    # Load model
    logger.info(f"Loading {args.method} model from {args.ckpt}...")
    if args.method == "tnc":
        model = TNCEncoder(config)
    elif args.method == "mae":
        model = MAETimeSeries(config)
    elif args.method == "byol":
        model = BYOLTimeSeries(config)
    
    model.load_state_dict(torch.load(args.ckpt, map_location=device))
    model = model.to(device)
    
    # Load and preprocess data
    logger.info("Loading data...")
    loader = DataIOLoader(config["dataset_config"])
    preprocessor = Preprocessor(dataset_config)
    segmenter = Segmenter(config)
    
    dfs = loader.load_all()
    all_windows = []
    all_metadata = []
    
    for df in dfs:
        df_processed, _ = preprocessor.preprocess_pipeline(df)
        channels = ["accX_norm", "accY_norm", "accZ_norm",
                   "gyroX_norm", "gyroY_norm", "gyroZ_norm"]
        windows, metadata = segmenter.create_windows(df_processed, channels)
        all_windows.append(windows)
        all_metadata.append(metadata)
    
    windows = np.concatenate(all_windows, axis=0)
    metadata = pd.concat(all_metadata, ignore_index=True)
    
    logger.info(f"Total windows: {len(windows)}")
    
    # Extract embeddings
    embeddings_df = extract_embeddings(
        model, windows, metadata, device,
        batch_size=config["training"]["batch_size"]
    )
    
    # Save
    output_dir = Path(config.get("embeddings_dir", "./embeddings"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "embeddings.parquet"
    embeddings_df.to_parquet(output_path, index=False)
    
    logger.info(f"Embeddings saved to {output_path}")
    logger.info(f"Shape: {embeddings_df.shape}")


if __name__ == "__main__":
    main()
