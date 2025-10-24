"""
Self-supervised learning training script.
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import numpy as np
from pathlib import Path
import logging
import argparse
from typing import Dict, Optional
from tqdm import tqdm

from .dataio import load_config, DataLoader as DataIOLoader
from .preprocessing import Preprocessor
from .segmentation import Segmenter
from .aug import TorchAugmenter
from .models import TNCEncoder, MAETimeSeries, BYOLTimeSeries
from .losses import CombinedSSLLoss, mae_reconstruction_loss
from .models.byol_ts import byol_loss

logger = logging.getLogger(__name__)


class WindowDataset(Dataset):
    """Dataset of windowed sensor data."""
    
    def __init__(self, windows: np.ndarray, metadata: pd.DataFrame):
        self.windows = windows
        self.metadata = metadata
        
    def __len__(self):
        return len(self.windows)
    
    def __getitem__(self, idx):
        window = torch.from_numpy(self.windows[idx]).float()
        return window, idx


def train_tnc(model: nn.Module, train_loader: DataLoader, 
             config: Dict, device: str) -> None:
    """Train TNC model."""
    loss_fn = CombinedSSLLoss(config)
    augmenter = TorchAugmenter(config)
    
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config["training"]["learning_rate"],
        weight_decay=config["training"]["weight_decay"]
    )
    
    epochs = config["training"]["epochs"]
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        
        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}")
        for batch, _ in pbar:
            batch = batch.to(device)
            
            # Create positive pairs
            anchor, positive = augmenter.create_positive_pair(batch)
            
            # Generate negatives (from other samples in batch)
            batch_size = batch.size(0)
            neg_idx = torch.randperm(batch_size)[:min(64, batch_size)]
            negatives = batch[neg_idx]
            negatives = augmenter(negatives)
            
            # Forward pass
            anchor_emb = model(anchor)
            positive_emb = model(positive)
            neg_embs = model(negatives)
            
            # Compute loss
            losses = loss_fn(anchor_emb, positive_emb, neg_embs.unsqueeze(1))
            loss = losses["total"]
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            pbar.set_postfix({"loss": loss.item()})
        
        avg_loss = total_loss / len(train_loader)
        logger.info(f"Epoch {epoch+1}: avg_loss={avg_loss:.4f}")


def train_mae(model: nn.Module, train_loader: DataLoader,
             config: Dict, device: str) -> None:
    """Train MAE model."""
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config["training"]["learning_rate"],
        weight_decay=config["training"]["weight_decay"]
    )
    
    epochs = config["training"]["epochs"]
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        
        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}")
        for batch, _ in pbar:
            batch = batch.to(device)
            
            # Forward pass
            recon, mask, _ = model(batch)
            
            # Compute loss
            loss = mae_reconstruction_loss(recon, batch, mask)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            pbar.set_postfix({"loss": loss.item()})
        
        avg_loss = total_loss / len(train_loader)
        logger.info(f"Epoch {epoch+1}: avg_loss={avg_loss:.4f}")


def train_byol(model: nn.Module, train_loader: DataLoader,
              config: Dict, device: str) -> None:
    """Train BYOL model."""
    augmenter = TorchAugmenter(config)
    
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config["training"]["learning_rate"],
        weight_decay=config["training"]["weight_decay"]
    )
    
    epochs = config["training"]["epochs"]
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        
        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}")
        for batch, _ in pbar:
            batch = batch.to(device)
            
            # Create two views
            view1, view2 = augmenter.create_positive_pair(batch)
            
            # Forward pass
            (pred1, proj2), (pred2, proj1) = model(view1, view2)
            
            # Compute loss
            loss1 = byol_loss(pred1, proj2)
            loss2 = byol_loss(pred2, proj1)
            loss = loss1 + loss2
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            # Update target network
            model.update_target_network()
            
            total_loss += loss.item()
            pbar.set_postfix({"loss": loss.item()})
        
        avg_loss = total_loss / len(train_loader)
        logger.info(f"Epoch {epoch+1}: avg_loss={avg_loss:.4f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--method", type=str, choices=["tnc", "mae", "byol"], required=True)
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
    logger.info(f"Total windows: {len(windows)}")
    
    # Create dataset and dataloader
    import pandas as pd
    metadata = pd.concat(all_metadata, ignore_index=True)
    dataset = WindowDataset(windows, metadata)
    train_loader = DataLoader(
        dataset,
        batch_size=config["training"]["batch_size"],
        shuffle=True,
        num_workers=config["training"]["num_workers"]
    )
    
    # Create model
    logger.info(f"Creating {args.method} model...")
    if args.method == "tnc":
        model = TNCEncoder(config).to(device)
    elif args.method == "mae":
        model = MAETimeSeries(config).to(device)
    elif args.method == "byol":
        model = BYOLTimeSeries(config).to(device)
    
    # Train
    logger.info("Starting training...")
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.method == "tnc":
        train_tnc(model, train_loader, config, device)
    elif args.method == "mae":
        train_mae(model, train_loader, config, device)
    elif args.method == "byol":
        train_byol(model, train_loader, config, device)
    
    # Save model
    ckpt_path = output_dir / f"{args.method}_final.pt"
    torch.save(model.state_dict(), ckpt_path)
    logger.info(f"Model saved to {ckpt_path}")


if __name__ == "__main__":
    main()
