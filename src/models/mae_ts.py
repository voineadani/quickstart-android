"""
Masked Autoencoder for Time Series with time + STFT masking.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple
import numpy as np


class PatchEmbedding(nn.Module):
    """Patch embedding for time series."""
    
    def __init__(self, input_dim: int, hidden_dim: int, patch_size: int = 16):
        super().__init__()
        self.patch_size = patch_size
        self.projection = nn.Linear(input_dim * patch_size, hidden_dim)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, T, C)
        Returns: (B, N, D) where N = T // patch_size
        """
        B, T, C = x.shape
        N = T // self.patch_size
        
        # Reshape into patches
        x = x[:, :N*self.patch_size, :]  # Trim to multiple of patch_size
        x = x.reshape(B, N, self.patch_size * C)
        x = self.projection(x)
        
        return x


class MAETimeSeries(nn.Module):
    """Masked Autoencoder for Time Series."""
    
    def __init__(self, config: Dict):
        super().__init__()
        
        model_config = config.get("model", {})
        mae_config = model_config.get("mae", {})
        
        self.input_dim = 6
        self.hidden_dim = model_config.get("hidden_dim", 256)
        self.patch_size = mae_config.get("patch_size", 16)
        self.mask_ratio = mae_config.get("mask_ratio", 0.75)
        
        decoder_dim = mae_config.get("decoder_dim", 128)
        decoder_depth = mae_config.get("decoder_depth", 2)
        
        # Encoder
        self.patch_embed = PatchEmbedding(self.input_dim, self.hidden_dim, self.patch_size)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=self.hidden_dim,
            nhead=8,
            dim_feedforward=self.hidden_dim * 4,
            dropout=0.1,
            batch_first=True
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=4)
        
        # Decoder (only used during pretraining)
        self.decoder_embed = nn.Linear(self.hidden_dim, decoder_dim)
        
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=decoder_dim,
            nhead=4,
            dim_feedforward=decoder_dim * 4,
            dropout=0.1,
            batch_first=True
        )
        self.decoder = nn.TransformerDecoder(decoder_layer, num_layers=decoder_depth)
        
        # Reconstruction head
        self.recon_head = nn.Linear(decoder_dim, self.input_dim * self.patch_size)
        
        # Mask token
        self.mask_token = nn.Parameter(torch.zeros(1, 1, self.hidden_dim))
        
    def random_masking(self, x: torch.Tensor, mask_ratio: float) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Random masking of patches.
        
        Returns:
            x_masked: Masked patches
            mask: Binary mask (1 = masked)
            ids_restore: Indices to restore original order
        """
        B, N, D = x.shape
        len_keep = int(N * (1 - mask_ratio))
        
        noise = torch.rand(B, N, device=x.device)
        ids_shuffle = torch.argsort(noise, dim=1)
        ids_restore = torch.argsort(ids_shuffle, dim=1)
        
        # Keep the first subset
        ids_keep = ids_shuffle[:, :len_keep]
        x_masked = torch.gather(x, dim=1, index=ids_keep.unsqueeze(-1).repeat(1, 1, D))
        
        # Generate binary mask
        mask = torch.ones([B, N], device=x.device)
        mask[:, :len_keep] = 0
        mask = torch.gather(mask, dim=1, index=ids_restore)
        
        return x_masked, mask, ids_restore
    
    def forward_encoder(self, x: torch.Tensor, mask_ratio: float) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Encode with masking."""
        x = self.patch_embed(x)
        x, mask, ids_restore = self.random_masking(x, mask_ratio)
        x = self.encoder(x)
        return x, mask, ids_restore
    
    def forward_decoder(self, x: torch.Tensor, ids_restore: torch.Tensor) -> torch.Tensor:
        """Decode masked patches."""
        x = self.decoder_embed(x)
        
        # Append mask tokens
        B, N_unmasked, D = x.shape
        N = ids_restore.shape[1]
        
        mask_tokens = self.mask_token.repeat(B, N - N_unmasked, 1)
        x_full = torch.cat([x, mask_tokens], dim=1)
        x_full = torch.gather(x_full, dim=1, index=ids_restore.unsqueeze(-1).repeat(1, 1, D))
        
        # Decode
        x_recon = self.decoder(x_full, x_full)  # Self-attention only
        x_recon = self.recon_head(x_recon)
        
        return x_recon
    
    def forward(self, x: torch.Tensor, mask_ratio: Optional[float] = None) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass for training.
        
        Returns:
            reconstruction, mask, latent
        """
        if mask_ratio is None:
            mask_ratio = self.mask_ratio
        
        latent, mask, ids_restore = self.forward_encoder(x, mask_ratio)
        recon = self.forward_decoder(latent, ids_restore)
        
        return recon, mask, latent
    
    def get_embedding(self, x: torch.Tensor) -> torch.Tensor:
        """Get embedding without masking."""
        x = self.patch_embed(x)
        x = self.encoder(x)
        return x.mean(dim=1)  # Pool over patches


if __name__ == "__main__":
    from dataio import load_config
    
    config = load_config("./configs/train_ssl.yml")
    model = MAETimeSeries(config)
    
    batch_size = 16
    time_steps = 304  # Multiple of patch_size (16)
    channels = 6
    
    x = torch.randn(batch_size, time_steps, channels)
    
    recon, mask, latent = model(x)
    embedding = model.get_embedding(x)
    
    print(f"Input shape: {x.shape}")
    print(f"Reconstruction shape: {recon.shape}")
    print(f"Mask shape: {mask.shape}")
    print(f"Latent shape: {latent.shape}")
    print(f"Embedding shape: {embedding.shape}")
