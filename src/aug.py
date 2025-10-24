"""
Data augmentation for time series: rotations, jitter, scaling, time-warp, channel-drop, masking.
"""

import numpy as np
import torch
from typing import Dict, Optional, Tuple
from scipy import interpolate
import logging

logger = logging.getLogger(__name__)


class TimeSeriesAugmenter:
    """Augmentation strategies for sensor time series."""
    
    def __init__(self, config: Dict):
        aug_config = config.get("augmentation", {})
        
        self.rotation_degrees = aug_config.get("rotation_degrees", 15)
        self.jitter_sigma = aug_config.get("jitter_sigma", 0.05)
        self.scaling_range = aug_config.get("scaling_range", [0.9, 1.1])
        self.time_warp_rate = aug_config.get("time_warp_rate", 0.1)
        self.channel_drop_prob = aug_config.get("channel_drop_prob", 0.2)
        self.masking_ratio = aug_config.get("masking_ratio", 0.15)
        self.drop_imu_prob = aug_config.get("drop_imu_prob", 0.1)
        self.drop_gps_prob = aug_config.get("drop_gps_prob", 0.1)
        
    def rotation_3d(self, data: np.ndarray, max_angle: Optional[float] = None) -> np.ndarray:
        """
        Apply random 3D rotation to accelerometer/gyro data.
        
        Args:
            data: Array of shape (T, C) where C is divisible by 3
            max_angle: Max rotation angle in degrees
            
        Returns:
            Rotated data
        """
        if max_angle is None:
            max_angle = self.rotation_degrees
        
        data = data.copy()
        
        # Generate random rotation matrix
        angles = np.random.uniform(-max_angle, max_angle, size=3) * np.pi / 180
        
        # Rotation matrices
        cx, cy, cz = np.cos(angles)
        sx, sy, sz = np.sin(angles)
        
        Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
        Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
        Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
        
        R = Rz @ Ry @ Rx
        
        # Apply to each 3D vector
        for i in range(0, data.shape[1], 3):
            if i + 3 <= data.shape[1]:
                data[:, i:i+3] = data[:, i:i+3] @ R.T
        
        return data
    
    def jitter(self, data: np.ndarray, sigma: Optional[float] = None) -> np.ndarray:
        """Add Gaussian jitter."""
        if sigma is None:
            sigma = self.jitter_sigma
        
        noise = np.random.normal(0, sigma, data.shape)
        return data + noise
    
    def scaling(self, data: np.ndarray, 
               scale_range: Optional[Tuple[float, float]] = None) -> np.ndarray:
        """Apply random scaling."""
        if scale_range is None:
            scale_range = self.scaling_range
        
        scale = np.random.uniform(scale_range[0], scale_range[1])
        return data * scale
    
    def time_warp(self, data: np.ndarray, rate: Optional[float] = None) -> np.ndarray:
        """
        Apply time warping by randomly stretching/compressing time.
        
        Args:
            data: Array of shape (T, C)
            rate: Warping rate (higher = more warping)
            
        Returns:
            Time-warped data
        """
        if rate is None:
            rate = self.time_warp_rate
        
        T = data.shape[0]
        
        # Generate smooth random warp
        n_knots = max(3, int(T * rate))
        knot_indices = np.linspace(0, T-1, n_knots)
        knot_offsets = np.random.randn(n_knots) * T * 0.1
        knot_offsets[0] = 0  # Fix endpoints
        knot_offsets[-1] = 0
        
        # Interpolate to get warp for each timestep
        warp = np.interp(np.arange(T), knot_indices, knot_indices + knot_offsets)
        warp = np.clip(warp, 0, T-1)
        
        # Apply warp to each channel
        warped = np.zeros_like(data)
        for c in range(data.shape[1]):
            warped[:, c] = np.interp(np.arange(T), warp, data[:, c])
        
        return warped
    
    def channel_dropout(self, data: np.ndarray, 
                       drop_prob: Optional[float] = None) -> np.ndarray:
        """Randomly drop entire channels."""
        if drop_prob is None:
            drop_prob = self.channel_drop_prob
        
        data = data.copy()
        n_channels = data.shape[1]
        
        for c in range(n_channels):
            if np.random.rand() < drop_prob:
                data[:, c] = 0
        
        return data
    
    def masking(self, data: np.ndarray, 
               mask_ratio: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Random masking of time steps (for MAE-style training).
        
        Returns:
            Masked data and mask (1 = masked)
        """
        if mask_ratio is None:
            mask_ratio = self.masking_ratio
        
        T = data.shape[0]
        n_mask = int(T * mask_ratio)
        
        # Random masking indices
        mask_indices = np.random.choice(T, n_mask, replace=False)
        
        mask = np.zeros(T, dtype=bool)
        mask[mask_indices] = True
        
        masked_data = data.copy()
        masked_data[mask] = 0
        
        return masked_data, mask
    
    def cross_modal_dropout(self, data: np.ndarray, 
                           n_imu_channels: int = 6) -> np.ndarray:
        """
        Randomly drop IMU or GPS modality.
        
        Args:
            data: Array of shape (T, C) where first n_imu_channels are IMU
            n_imu_channels: Number of IMU channels (accel + gyro)
        """
        data = data.copy()
        
        if np.random.rand() < self.drop_imu_prob:
            # Drop IMU channels
            data[:, :n_imu_channels] = 0
            
        elif np.random.rand() < self.drop_gps_prob:
            # Drop GPS channels (everything after IMU)
            if data.shape[1] > n_imu_channels:
                data[:, n_imu_channels:] = 0
        
        return data
    
    def augment(self, data: np.ndarray, 
               augment_types: Optional[list] = None) -> np.ndarray:
        """
        Apply random combination of augmentations.
        
        Args:
            data: Array of shape (T, C)
            augment_types: List of augmentation names to apply (None = all)
            
        Returns:
            Augmented data
        """
        if augment_types is None:
            augment_types = ["rotation", "jitter", "scaling"]
        
        augmented = data.copy()
        
        if "rotation" in augment_types and np.random.rand() > 0.5:
            augmented = self.rotation_3d(augmented)
        
        if "jitter" in augment_types and np.random.rand() > 0.5:
            augmented = self.jitter(augmented)
        
        if "scaling" in augment_types and np.random.rand() > 0.5:
            augmented = self.scaling(augmented)
        
        if "time_warp" in augment_types and np.random.rand() > 0.3:
            augmented = self.time_warp(augmented)
        
        if "channel_drop" in augment_types and np.random.rand() > 0.3:
            augmented = self.channel_dropout(augmented)
        
        return augmented
    
    def create_positive_pair(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create positive pair for contrastive learning.
        
        Returns:
            Two differently augmented views of the same data
        """
        view1 = self.augment(data)
        view2 = self.augment(data)
        
        return view1, view2


class TorchAugmenter(torch.nn.Module):
    """PyTorch-compatible augmenter for use in training."""
    
    def __init__(self, config: Dict):
        super().__init__()
        self.augmenter = TimeSeriesAugmenter(config)
        
    def forward(self, x: torch.Tensor, 
               augment_types: Optional[list] = None) -> torch.Tensor:
        """
        Apply augmentation to batch.
        
        Args:
            x: Tensor of shape (B, T, C)
            augment_types: List of augmentation types
            
        Returns:
            Augmented tensor
        """
        batch_size = x.shape[0]
        device = x.device
        
        # Convert to numpy, augment, convert back
        augmented = []
        for i in range(batch_size):
            data_np = x[i].cpu().numpy()
            aug_np = self.augmenter.augment(data_np, augment_types)
            augmented.append(torch.from_numpy(aug_np))
        
        return torch.stack(augmented).to(device)
    
    def create_positive_pair(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Create positive pair for contrastive learning."""
        view1 = self.forward(x)
        view2 = self.forward(x)
        return view1, view2


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test augmentations
    from dataio import load_config
    
    config = load_config("./configs/train_ssl.yml")
    augmenter = TimeSeriesAugmenter(config)
    
    # Generate dummy data
    T, C = 300, 6  # 3s at 100Hz, 6 channels (accel + gyro)
    data = np.random.randn(T, C)
    
    print("Original shape:", data.shape)
    
    # Test individual augmentations
    rotated = augmenter.rotation_3d(data)
    print("Rotated shape:", rotated.shape)
    
    jittered = augmenter.jitter(data)
    print("Jittered shape:", jittered.shape)
    
    warped = augmenter.time_warp(data)
    print("Warped shape:", warped.shape)
    
    masked, mask = augmenter.masking(data)
    print(f"Masked shape: {masked.shape}, masked {mask.sum()}/{len(mask)} samples")
    
    # Test full augmentation
    augmented = augmenter.augment(data)
    print("Augmented shape:", augmented.shape)
    
    # Test positive pairs
    view1, view2 = augmenter.create_positive_pair(data)
    print(f"Positive pair shapes: {view1.shape}, {view2.shape}")
