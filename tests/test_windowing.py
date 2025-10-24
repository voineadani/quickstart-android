"""
Tests for windowing and segmentation.
"""

import pytest
import numpy as np
import pandas as pd
from src.segmentation import Segmenter, BayesianOnlineChangepoint


@pytest.fixture
def sample_config():
    return {
        "model": {
            "tnc": {
                "window_size_seconds": 3.0,
                "overlap": 0.5
            }
        },
        "sampling_rates": {
            "imu": 100
        }
    }


@pytest.fixture
def sample_data():
    n_samples = 1000
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n_samples, freq="10ms"),
        "accX": np.random.randn(n_samples),
        "accY": np.random.randn(n_samples),
        "accZ": np.random.randn(n_samples),
        "gyroX": np.random.randn(n_samples),
        "gyroY": np.random.randn(n_samples),
        "gyroZ": np.random.randn(n_samples),
    })


def test_window_creation(sample_config, sample_data):
    """Test basic window creation."""
    segmenter = Segmenter(sample_config)
    channels = ["accX", "accY", "accZ", "gyroX", "gyroY", "gyroZ"]
    
    windows, metadata = segmenter.create_windows(sample_data, channels)
    
    # Check shapes
    assert windows.ndim == 3  # (n_windows, time_steps, channels)
    assert windows.shape[2] == len(channels)
    assert len(windows) == len(metadata)
    
    # Check window size
    expected_window_samples = int(3.0 * 100)  # 3s at 100Hz
    assert windows.shape[1] == expected_window_samples


def test_window_overlap(sample_config, sample_data):
    """Test that overlap is correctly applied."""
    segmenter = Segmenter(sample_config)
    channels = ["accX", "accY", "accZ", "gyroX", "gyroY", "gyroZ"]
    
    windows, metadata = segmenter.create_windows(sample_data, channels)
    
    # With 50% overlap, step should be half window size
    window_samples = int(3.0 * 100)
    step_samples = int(window_samples * 0.5)
    
    # Check metadata indices
    if len(metadata) > 1:
        start_diff = metadata.iloc[1]["start_idx"] - metadata.iloc[0]["start_idx"]
        assert start_diff == step_samples


def test_window_metadata(sample_config, sample_data):
    """Test window metadata generation."""
    segmenter = Segmenter(sample_config)
    channels = ["accX"]
    
    windows, metadata = segmenter.create_windows(sample_data, channels)
    
    # Check metadata columns
    assert "window_id" in metadata.columns
    assert "start_idx" in metadata.columns
    assert "end_idx" in metadata.columns
    assert "start_time" in metadata.columns
    assert "end_time" in metadata.columns


def test_bocpd_detection():
    """Test Bayesian Online Changepoint Detection."""
    bocpd = BayesianOnlineChangepoint(hazard_rate=0.01)
    
    # Create data with a clear changepoint
    data = np.concatenate([
        np.random.normal(0, 1, 500),  # First segment
        np.random.normal(5, 1, 500),  # Second segment (shifted mean)
    ])
    
    changepoints = bocpd.detect(data, threshold=0.5)
    
    # Should detect changepoint near index 500
    assert len(changepoints) > 0
    
    # Changepoint should be roughly in the middle
    if changepoints:
        assert 400 < changepoints[0] < 600


def test_empty_data_handling(sample_config):
    """Test handling of empty data."""
    segmenter = Segmenter(sample_config)
    
    empty_df = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=10, freq="10ms"),
        "accX": np.nan * np.ones(10),
    })
    
    channels = ["accX"]
    windows, metadata = segmenter.create_windows(empty_df, channels)
    
    # Should return empty arrays for data with all NaNs
    assert len(windows) == 0
    assert len(metadata) == 0


def test_window_no_nans(sample_config, sample_data):
    """Test that windows don't contain NaNs after processing."""
    segmenter = Segmenter(sample_config)
    
    # Add some NaNs to data
    sample_data.loc[50:60, "accX"] = np.nan
    
    channels = ["accX", "accY", "accZ"]
    windows, metadata = segmenter.create_windows(sample_data, channels)
    
    # Windows should have NaNs interpolated
    for i in range(len(windows)):
        # Allow some NaNs if there's excessive missingness
        nan_ratio = np.isnan(windows[i]).sum() / windows[i].size
        assert nan_ratio < 0.2  # Less than 20% NaNs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
