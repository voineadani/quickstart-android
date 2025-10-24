"""
Loss functions: InfoNCE, BYOL, time-warp consistency.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional


class InfoNCELoss(nn.Module):
    """InfoNCE contrastive loss for TNC."""
    
    def __init__(self, temperature: float = 0.07):
        super().__init__()
        self.temperature = temperature
        
    def forward(self, anchor: torch.Tensor, positive: torch.Tensor, 
               negatives: torch.Tensor) -> torch.Tensor:
        """
        Args:
            anchor: (B, D) anchor embeddings
            positive: (B, D) positive embeddings
            negatives: (B, K, D) negative embeddings
            
        Returns:
            Loss scalar
        """
        # Normalize
        anchor = F.normalize(anchor, dim=-1)
        positive = F.normalize(positive, dim=-1)
        negatives = F.normalize(negatives, dim=-1)
        
        # Positive similarity
        pos_sim = (anchor * positive).sum(dim=-1) / self.temperature  # (B,)
        
        # Negative similarities
        neg_sim = torch.einsum('bd,bkd->bk', anchor, negatives) / self.temperature  # (B, K)
        
        # InfoNCE loss
        logits = torch.cat([pos_sim.unsqueeze(1), neg_sim], dim=1)  # (B, K+1)
        labels = torch.zeros(logits.shape[0], dtype=torch.long, device=logits.device)
        
        loss = F.cross_entropy(logits, labels)
        
        return loss


class TimeWarpConsistencyLoss(nn.Module):
    """Consistency loss for time-warped augmentations."""
    
    def __init__(self):
        super().__init__()
        
    def forward(self, embedding1: torch.Tensor, embedding2: torch.Tensor) -> torch.Tensor:
        """
        Embeddings should be similar despite time warping.
        
        Args:
            embedding1, embedding2: (B, D) embeddings of warped versions
            
        Returns:
            Loss scalar (MSE in normalized space)
        """
        embedding1 = F.normalize(embedding1, dim=-1)
        embedding2 = F.normalize(embedding2, dim=-1)
        
        loss = F.mse_loss(embedding1, embedding2)
        
        return loss


class CombinedSSLLoss(nn.Module):
    """Combined loss for self-supervised learning."""
    
    def __init__(self, config: dict):
        super().__init__()
        
        loss_config = config.get("loss", {})
        temperature = loss_config.get("temperature", 0.07)
        
        self.contrastive_weight = loss_config.get("contrastive_weight", 1.0)
        self.time_warp_weight = loss_config.get("time_warp_weight", 0.5)
        
        self.infonce = InfoNCELoss(temperature)
        self.time_warp = TimeWarpConsistencyLoss()
        
    def forward(self, anchor: torch.Tensor, positive: torch.Tensor,
               negatives: torch.Tensor, warped_anchor: Optional[torch.Tensor] = None,
               warped_positive: Optional[torch.Tensor] = None) -> dict:
        """
        Compute combined loss.
        
        Returns:
            Dictionary with individual and total losses
        """
        losses = {}
        
        # Contrastive loss
        contrastive_loss = self.infonce(anchor, positive, negatives)
        losses['contrastive'] = contrastive_loss
        
        total_loss = self.contrastive_weight * contrastive_loss
        
        # Time-warp consistency (if provided)
        if warped_anchor is not None and warped_positive is not None:
            warp_loss = self.time_warp(warped_anchor, anchor) + \
                       self.time_warp(warped_positive, positive)
            losses['time_warp'] = warp_loss
            total_loss += self.time_warp_weight * warp_loss
        
        losses['total'] = total_loss
        
        return losses


def mae_reconstruction_loss(pred: torch.Tensor, target: torch.Tensor, 
                           mask: torch.Tensor) -> torch.Tensor:
    """
    MAE reconstruction loss (MSE on masked patches).
    
    Args:
        pred: (B, N, P*C) predicted patches
        target: (B, T, C) original data
        mask: (B, N) binary mask (1 = masked)
        
    Returns:
        Loss scalar
    """
    B, N, _ = pred.shape
    B, T, C = target.shape
    
    patch_size = T // N
    
    # Reshape target into patches
    target = target[:, :N*patch_size, :]
    target = target.reshape(B, N, patch_size * C)
    
    # Compute loss only on masked patches
    loss = (pred - target) ** 2
    loss = loss.mean(dim=-1)  # (B, N)
    loss = (loss * mask).sum() / mask.sum()
    
    return loss


if __name__ == "__main__":
    # Test InfoNCE
    infonce = InfoNCELoss()
    
    B, D, K = 32, 128, 64
    anchor = torch.randn(B, D)
    positive = torch.randn(B, D)
    negatives = torch.randn(B, K, D)
    
    loss = infonce(anchor, positive, negatives)
    print(f"InfoNCE loss: {loss.item():.4f}")
    
    # Test time-warp consistency
    warp_loss_fn = TimeWarpConsistencyLoss()
    emb1 = torch.randn(B, D)
    emb2 = torch.randn(B, D)
    
    warp_loss = warp_loss_fn(emb1, emb2)
    print(f"Time-warp loss: {warp_loss.item():.4f}")
    
    # Test MAE loss
    pred = torch.randn(16, 19, 96)  # 19 patches, 96 = 16*6
    target = torch.randn(16, 304, 6)
    mask = torch.randint(0, 2, (16, 19)).float()
    
    mae_loss = mae_reconstruction_loss(pred, target, mask)
    print(f"MAE loss: {mae_loss.item():.4f}")
