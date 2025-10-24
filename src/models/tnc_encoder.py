"""
TNC (Temporal Neighborhood Coding) Encoder with Conv/Transformer hybrid.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Optional
import math


class PositionalEncoding(nn.Module):
    """Positional encoding for transformer."""
    
    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, d_model)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, T, D)"""
        return x + self.pe[:x.size(1)]


class ConvEncoder(nn.Module):
    """Convolutional encoder for local feature extraction."""
    
    def __init__(self, input_dim: int, hidden_dim: int):
        super().__init__()
        self.conv1 = nn.Conv1d(input_dim, hidden_dim // 2, kernel_size=7, padding=3)
        self.conv2 = nn.Conv1d(hidden_dim // 2, hidden_dim, kernel_size=5, padding=2)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.bn1 = nn.BatchNorm1d(hidden_dim // 2)
        self.bn2 = nn.BatchNorm1d(hidden_dim)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, T, C)
        Returns: (B, D)
        """
        x = x.transpose(1, 2)  # (B, C, T)
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.pool(x).squeeze(-1)  # (B, D)
        return x


class TransformerEncoder(nn.Module):
    """Transformer encoder for global dependencies."""
    
    def __init__(self, input_dim: int, hidden_dim: int, num_layers: int, 
                 num_heads: int = 8, dropout: float = 0.1):
        super().__init__()
        self.embedding = nn.Linear(input_dim, hidden_dim)
        self.pos_encoder = PositionalEncoding(hidden_dim)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
        self.pool = nn.AdaptiveAvgPool1d(1)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, T, C)
        Returns: (B, D)
        """
        x = self.embedding(x)  # (B, T, D)
        x = self.pos_encoder(x)
        x = self.transformer(x)  # (B, T, D)
        x = x.transpose(1, 2)  # (B, D, T)
        x = self.pool(x).squeeze(-1)  # (B, D)
        return x


class TNCEncoder(nn.Module):
    """TNC encoder with Conv/Transformer hybrid architecture."""
    
    def __init__(self, config: Dict):
        super().__init__()
        
        model_config = config.get("model", {})
        encoder_type = model_config.get("encoder_type", "conv_transformer")
        
        self.input_dim = 6  # Default: accel + gyro
        self.hidden_dim = model_config.get("hidden_dim", 256)
        self.num_layers = model_config.get("num_layers", 4)
        self.dropout = model_config.get("dropout", 0.1)
        
        if encoder_type == "conv":
            self.encoder = ConvEncoder(self.input_dim, self.hidden_dim)
            
        elif encoder_type == "transformer":
            self.encoder = TransformerEncoder(
                self.input_dim, self.hidden_dim, 
                self.num_layers, dropout=self.dropout
            )
            
        elif encoder_type == "conv_transformer":
            # Hybrid: Conv for local, Transformer for global
            self.conv_encoder = ConvEncoder(self.input_dim, self.hidden_dim // 2)
            self.transformer_encoder = TransformerEncoder(
                self.input_dim, self.hidden_dim // 2,
                self.num_layers // 2, dropout=self.dropout
            )
            self.fusion = nn.Linear(self.hidden_dim, self.hidden_dim)
            self.encoder_type = "hybrid"
        else:
            raise ValueError(f"Unknown encoder type: {encoder_type}")
        
        # Projection head for contrastive learning
        self.projection = nn.Sequential(
            nn.Linear(self.hidden_dim, self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.hidden_dim // 2)
        )
    
    def forward(self, x: torch.Tensor, return_projection: bool = True) -> torch.Tensor:
        """
        Args:
            x: (B, T, C) input tensor
            return_projection: Whether to return projection or encoding
            
        Returns:
            Embedding tensor
        """
        if hasattr(self, 'encoder_type') and self.encoder_type == "hybrid":
            # Hybrid encoding
            conv_feat = self.conv_encoder(x)
            trans_feat = self.transformer_encoder(x)
            encoding = torch.cat([conv_feat, trans_feat], dim=-1)
            encoding = self.fusion(encoding)
        else:
            encoding = self.encoder(x)
        
        if return_projection:
            return self.projection(encoding)
        return encoding
    
    def get_embedding(self, x: torch.Tensor) -> torch.Tensor:
        """Get embedding without projection."""
        return self.forward(x, return_projection=False)


if __name__ == "__main__":
    from dataio import load_config
    
    config = load_config("./configs/train_ssl.yml")
    model = TNCEncoder(config)
    
    # Test forward pass
    batch_size = 16
    time_steps = 300  # 3s at 100Hz
    channels = 6
    
    x = torch.randn(batch_size, time_steps, channels)
    
    projection = model(x, return_projection=True)
    embedding = model(x, return_projection=False)
    
    print(f"Input shape: {x.shape}")
    print(f"Projection shape: {projection.shape}")
    print(f"Embedding shape: {embedding.shape}")
