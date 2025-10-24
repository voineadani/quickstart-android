"""
BYOL/SimSiam-style non-contrastive learning for time series.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict
import copy


class MLP(nn.Module):
    """Multi-layer perceptron."""
    
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class BYOLTimeSeries(nn.Module):
    """BYOL for time series with EMA target network."""
    
    def __init__(self, config: Dict):
        super().__init__()
        
        # Import encoder
        from .tnc_encoder import TNCEncoder
        
        model_config = config.get("model", {})
        byol_config = model_config.get("byol", {})
        
        self.hidden_dim = model_config.get("hidden_dim", 256)
        projection_dim = byol_config.get("projection_dim", 256)
        predictor_dim = byol_config.get("predictor_dim", 128)
        self.ema_decay = byol_config.get("ema_decay", 0.996)
        
        # Online network
        self.online_encoder = TNCEncoder(config)
        self.online_projector = MLP(self.hidden_dim, projection_dim, projection_dim)
        self.predictor = MLP(projection_dim, predictor_dim, projection_dim)
        
        # Target network (EMA of online)
        self.target_encoder = copy.deepcopy(self.online_encoder)
        self.target_projector = copy.deepcopy(self.online_projector)
        
        # Freeze target network
        for param in self.target_encoder.parameters():
            param.requires_grad = False
        for param in self.target_projector.parameters():
            param.requires_grad = False
    
    @torch.no_grad()
    def update_target_network(self):
        """Update target network with EMA."""
        for online_params, target_params in zip(
            self.online_encoder.parameters(), self.target_encoder.parameters()
        ):
            target_params.data = (
                self.ema_decay * target_params.data + 
                (1 - self.ema_decay) * online_params.data
            )
        
        for online_params, target_params in zip(
            self.online_projector.parameters(), self.target_projector.parameters()
        ):
            target_params.data = (
                self.ema_decay * target_params.data + 
                (1 - self.ema_decay) * online_params.data
            )
    
    def forward(self, x1: torch.Tensor, x2: torch.Tensor) -> tuple:
        """
        Forward pass with two augmented views.
        
        Args:
            x1, x2: (B, T, C) augmented views
            
        Returns:
            (pred1, proj2), (pred2, proj1) for loss computation
        """
        # Online network
        online_enc1 = self.online_encoder.get_embedding(x1)
        online_proj1 = self.online_projector(online_enc1)
        online_pred1 = self.predictor(online_proj1)
        
        online_enc2 = self.online_encoder.get_embedding(x2)
        online_proj2 = self.online_projector(online_enc2)
        online_pred2 = self.predictor(online_proj2)
        
        # Target network
        with torch.no_grad():
            target_enc1 = self.target_encoder.get_embedding(x1)
            target_proj1 = self.target_projector(target_enc1)
            
            target_enc2 = self.target_encoder.get_embedding(x2)
            target_proj2 = self.target_projector(target_enc2)
        
        return (online_pred1, target_proj2), (online_pred2, target_proj1)
    
    def get_embedding(self, x: torch.Tensor) -> torch.Tensor:
        """Get embedding from online encoder."""
        return self.online_encoder.get_embedding(x)


def byol_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """
    BYOL loss: mean squared error in normalized space.
    
    Args:
        pred: Predicted projection
        target: Target projection (detached)
        
    Returns:
        Loss scalar
    """
    pred = F.normalize(pred, dim=-1)
    target = F.normalize(target, dim=-1)
    return 2 - 2 * (pred * target).sum(dim=-1).mean()


if __name__ == "__main__":
    from dataio import load_config
    
    config = load_config("./configs/train_ssl.yml")
    model = BYOLTimeSeries(config)
    
    batch_size = 16
    time_steps = 300
    channels = 6
    
    x1 = torch.randn(batch_size, time_steps, channels)
    x2 = torch.randn(batch_size, time_steps, channels)
    
    (pred1, proj2), (pred2, proj1) = model(x1, x2)
    
    loss1 = byol_loss(pred1, proj2)
    loss2 = byol_loss(pred2, proj1)
    total_loss = loss1 + loss2
    
    print(f"Input shapes: {x1.shape}, {x2.shape}")
    print(f"Prediction shapes: {pred1.shape}, {pred2.shape}")
    print(f"Loss: {total_loss.item():.4f}")
    
    # Test embedding
    embedding = model.get_embedding(x1)
    print(f"Embedding shape: {embedding.shape}")
