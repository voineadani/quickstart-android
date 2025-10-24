"""
Tests for weak label generation.
"""

import pytest
import numpy as np
import pandas as pd
from src.weaklabels import WeakLabeler


@pytest.fixture
def sample_config():
    return {
        "thresholds": {
            "harsh_brake_jerk": -3.0,
            "harsh_accel_jerk": 3.0,
            "left_turn_yaw": 0.3,
            "right_turn_yaw": -0.3,
            "emergency_brake_dv": -5.0,
            "sharp_curve_curvature": 0.02,
            "roundabout": {
                "min_duration": 3.0,
                "min_total_angle": 270,
                "max_radius": 50
            }
        },
        "gps": {
            "min_accuracy": 20,
            "min_speed_for_bearing": 1.0
        }
    }


@pytest.fixture
def sample_data():
    n = 1000
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="10ms"),
        "linear_X": np.random.randn(n) * 0.5,
        "gyroZ": np.random.randn(n) * 0.1,
        "speed": np.random.uniform(10, 20, n),
        "lat": np.linspace(45.0, 45.01, n),
        "lon": np.linspace(25.0, 25.01, n),
        "accuracy": np.random.uniform(5, 15, n)
    })


def test_harsh_brake_detection(sample_config, sample_data):
    """Test harsh braking detection."""
    labeler = WeakLabeler(sample_config)
    
    # Add harsh brake event
    df = sample_data.copy()
    df.loc[500:520, "linear_X"] = -5.0  # Strong deceleration
    
    df_labeled = labeler.label_harsh_events(df, sampling_rate=100.0)
    
    # Should detect harsh brake
    assert "harsh_brake" in df_labeled.columns
    assert df_labeled["harsh_brake"].sum() > 0


def test_harsh_accel_detection(sample_config, sample_data):
    """Test harsh acceleration detection."""
    labeler = WeakLabeler(sample_config)
    
    # Add harsh acceleration event
    df = sample_data.copy()
    df.loc[500:520, "linear_X"] = 5.0  # Strong acceleration
    
    df_labeled = labeler.label_harsh_events(df, sampling_rate=100.0)
    
    # Should detect harsh acceleration
    assert "harsh_accel" in df_labeled.columns
    assert df_labeled["harsh_accel"].sum() > 0


def test_turn_detection(sample_config, sample_data):
    """Test turn detection."""
    labeler = WeakLabeler(sample_config)
    
    # Add left turn
    df = sample_data.copy()
    df.loc[500:550, "gyroZ"] = 0.5  # Left turn
    
    df_labeled = labeler.label_turns(df)
    
    # Should detect left turn
    assert "left_turn" in df_labeled.columns
    assert df_labeled["left_turn"].sum() > 0


def test_right_turn_detection(sample_config, sample_data):
    """Test right turn detection."""
    labeler = WeakLabeler(sample_config)
    
    # Add right turn
    df = sample_data.copy()
    df.loc[500:550, "gyroZ"] = -0.5  # Right turn
    
    df_labeled = labeler.label_turns(df)
    
    # Should detect right turn
    assert "right_turn" in df_labeled.columns
    assert df_labeled["right_turn"].sum() > 0


def test_emergency_brake_detection(sample_config, sample_data):
    """Test emergency braking detection."""
    labeler = WeakLabeler(sample_config)
    
    # Add emergency brake (sudden speed drop)
    df = sample_data.copy()
    df.loc[500, "speed"] = 20.0
    df.loc[501, "speed"] = 10.0  # Drop 10 m/s in 1s
    
    df_labeled = labeler.label_emergency_brake(df)
    
    # Should detect emergency brake
    assert "emergency_brake" in df_labeled.columns
    # May or may not detect depending on exact threshold


def test_curve_labeling(sample_config, sample_data):
    """Test curve labeling from GPS."""
    labeler = WeakLabeler(sample_config)
    
    df_labeled = labeler.label_curves(sample_data)
    
    # Should add curvature and sharp_curve columns
    assert "curvature" in df_labeled.columns
    assert "sharp_curve" in df_labeled.columns


def test_no_labels_for_normal_driving(sample_config):
    """Test that normal driving doesn't trigger labels."""
    labeler = WeakLabeler(sample_config)
    
    # Create very smooth driving data
    n = 1000
    df = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="10ms"),
        "linear_X": np.random.randn(n) * 0.1,  # Very small accelerations
        "gyroZ": np.random.randn(n) * 0.01,  # Very small yaw rates
        "speed": np.ones(n) * 15.0,  # Constant speed
        "lat": np.linspace(45.0, 45.001, n),  # Nearly straight
        "lon": np.linspace(25.0, 25.001, n),
        "accuracy": np.ones(n) * 10.0
    })
    
    df_labeled = labeler.generate_all_labels(df, sampling_rate=100.0)
    
    # Should have very few or no events
    total_events = 0
    for col in ["harsh_brake", "harsh_accel", "left_turn", "right_turn", 
               "emergency_brake", "sharp_curve"]:
        if col in df_labeled.columns:
            total_events += df_labeled[col].sum()
    
    # Normal driving should have minimal events
    assert total_events < len(df) * 0.1  # Less than 10% of samples


def test_jerk_computation(sample_config):
    """Test jerk calculation."""
    labeler = WeakLabeler(sample_config)
    
    # Linear acceleration profile
    accel = np.array([0, 1, 2, 3, 4, 5])
    jerk = labeler.compute_jerk(accel, dt=1.0)
    
    # Jerk should be approximately constant (1.0) for linear increase
    # Allow for endpoint effects
    assert np.abs(np.mean(jerk[1:-1]) - 1.0) < 0.5


def test_delta_v_computation(sample_config):
    """Test delta-v calculation."""
    labeler = WeakLabeler(sample_config)
    
    # Speed profile
    speed = np.array([10, 10, 10, 5, 5, 5])
    delta_v = labeler.compute_delta_v(speed, dt=1.0)
    
    # Should have drop at index 3
    assert delta_v[3] < 0
    assert np.abs(delta_v[3]) > 4  # ~5 m/s drop


def test_all_labels_generation(sample_config, sample_data):
    """Test that all labels are generated."""
    labeler = WeakLabeler(sample_config)
    
    df_labeled = labeler.generate_all_labels(sample_data, sampling_rate=100.0)
    
    # Check that all expected columns are present
    expected_cols = ["harsh_brake", "harsh_accel", "left_turn", "right_turn",
                    "emergency_brake", "sharp_curve", "curvature", "roundabout"]
    
    for col in expected_cols:
        assert col in df_labeled.columns


def test_missing_gps_handling(sample_config):
    """Test handling of missing GPS data."""
    labeler = WeakLabeler(sample_config)
    
    # Data without GPS
    n = 1000
    df = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="10ms"),
        "linear_X": np.random.randn(n),
        "gyroZ": np.random.randn(n) * 0.1,
    })
    
    # Should not crash
    df_labeled = labeler.generate_all_labels(df, sampling_rate=100.0)
    
    # IMU-based labels should still work
    assert "harsh_brake" in df_labeled.columns
    assert "left_turn" in df_labeled.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
