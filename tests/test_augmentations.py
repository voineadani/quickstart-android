"""
Tests for data augmentation.
"""

import pytest
import numpy as np
from src.aug import TimeSeriesAugmenter


@pytest.fixture
def sample_config():
    return {
        "augmentation": {
            "rotation_degrees": 15,
            "jitter_sigma": 0.05,
            "scaling_range": [0.9, 1.1],
            "time_warp_rate": 0.1,
            "channel_drop_prob": 0.2,
            "masking_ratio": 0.15,
            "drop_imu_prob": 0.1,
            "drop_gps_prob": 0.1,
        }
    }


@pytest.fixture
def sample_data():
    """Generate sample time series data."""
    T, C = 300, 6  # 3s at 100Hz, 6 channels
    return np.random.randn(T, C)


def test_rotation_preserves_shape(sample_config, sample_data):
    """Test that rotation preserves data shape."""
    augmenter = TimeSeriesAugmenter(sample_config)
    
    rotated = augmenter.rotation_3d(sample_data)
    
    assert rotated.shape == sample_data.shape


def test_rotation_changes_values(sample_config, sample_data):
    """Test that rotation actually changes values."""
    augmenter = TimeSeriesAugmenter(sample_config)
    
    rotated = augmenter.rotation_3d(sample_data, max_angle=45)
    
    # Should be different after rotation
    assert not np.allclose(rotated, sample_data)


def test_jitter_preserves_shape(sample_config, sample_data):
    """Test that jitter preserves shape."""
    augmenter = TimeSeriesAugmenter(sample_config)
    
    jittered = augmenter.jitter(sample_data)
    
    assert jittered.shape == sample_data.shape


def test_jitter_bounded(sample_config, sample_data):
    """Test that jitter is bounded."""
    augmenter = TimeSeriesAugmenter(sample_config)
    sigma = 0.1
    
    jittered = augmenter.jitter(sample_data, sigma=sigma)
    
    # Jitter should be small relative to original
    diff = np.abs(jittered - sample_data)
    # Most differences should be within 3 sigma
    assert np.percentile(diff, 99) < 3 * sigma


def test_scaling_preserves_shape(sample_config, sample_data):
    """Test that scaling preserves shape."""
    augmenter = TimeSeriesAugmenter(sample_config)
    
    scaled = augmenter.scaling(sample_data)
    
    assert scaled.shape == sample_data.shape


def test_scaling_in_range(sample_config):
    """Test that scaling is in specified range."""
    config = sample_config.copy()
    config["augmentation"]["scaling_range"] = [0.8, 1.2]
    
    augmenter = TimeSeriesAugmenter(config)
    
    data = np.ones((100, 6))
    
    # Run multiple times to check range
    scales = []
    for _ in range(100):
        scaled = augmenter.scaling(data)
        scale = scaled[0, 0]  # All should be same scale
        scales.append(scale)
    
    scales = np.array(scales)
    assert scales.min() >= 0.8
    assert scales.max() <= 1.2


def test_time_warp_preserves_shape(sample_config, sample_data):
    """Test that time warp preserves shape."""
    augmenter = TimeSeriesAugmenter(sample_config)
    
    warped = augmenter.time_warp(sample_data)
    
    assert warped.shape == sample_data.shape


def test_channel_dropout_zeroes_channels(sample_config, sample_data):
    """Test that channel dropout zeroes some channels."""
    augmenter = TimeSeriesAugmenter(sample_config)
    
    dropped = augmenter.channel_dropout(sample_data, drop_prob=1.0)
    
    # With drop_prob=1.0, all channels should be zeroed
    assert np.allclose(dropped, 0)


def test_masking_masks_timesteps(sample_config, sample_data):
    """Test that masking masks correct proportion of timesteps."""
    augmenter = TimeSeriesAugmenter(sample_config)
    
    mask_ratio = 0.25
    masked_data, mask = augmenter.masking(sample_data, mask_ratio=mask_ratio)
    
    # Check mask size
    assert len(mask) == len(sample_data)
    
    # Check mask ratio
    actual_ratio = mask.sum() / len(mask)
    assert np.isclose(actual_ratio, mask_ratio, atol=0.05)
    
    # Check that masked positions are zeroed
    assert np.allclose(masked_data[mask], 0)


def test_cross_modal_dropout(sample_config):
    """Test cross-modal dropout."""
    augmenter = TimeSeriesAugmenter(sample_config)
    
    # 6 IMU channels + 2 GPS channels
    data = np.random.randn(100, 8)
    
    # Force IMU dropout
    augmenter.drop_imu_prob = 1.0
    augmenter.drop_gps_prob = 0.0
    
    dropped = augmenter.cross_modal_dropout(data, n_imu_channels=6)
    
    # IMU channels should be zeroed
    assert np.allclose(dropped[:, :6], 0)
    # GPS channels should be intact
    assert not np.allclose(dropped[:, 6:], 0)


def test_augment_composition(sample_config, sample_data):
    """Test that augment applies multiple augmentations."""
    augmenter = TimeSeriesAugmenter(sample_config)
    
    augmented = augmenter.augment(
        sample_data,
        augment_types=["rotation", "jitter", "scaling"]
    )
    
    # Should be different from original
    assert not np.allclose(augmented, sample_data)
    
    # Should preserve shape
    assert augmented.shape == sample_data.shape


def test_positive_pair_creation(sample_config, sample_data):
    """Test creation of positive pairs."""
    augmenter = TimeSeriesAugmenter(sample_config)
    
    view1, view2 = augmenter.create_positive_pair(sample_data)
    
    # Both views should have same shape as original
    assert view1.shape == sample_data.shape
    assert view2.shape == sample_data.shape
    
    # Views should be different from each other
    assert not np.allclose(view1, view2)
    
    # Views should be different from original
    assert not np.allclose(view1, sample_data)
    assert not np.allclose(view2, sample_data)


def test_deterministic_with_seed(sample_config, sample_data):
    """Test that augmentations are deterministic with seed."""
    np.random.seed(42)
    augmenter1 = TimeSeriesAugmenter(sample_config)
    result1 = augmenter1.jitter(sample_data)
    
    np.random.seed(42)
    augmenter2 = TimeSeriesAugmenter(sample_config)
    result2 = augmenter2.jitter(sample_data)
    
    assert np.allclose(result1, result2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
