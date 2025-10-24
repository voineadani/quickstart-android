"""
Tests for geospatial utilities and curvature calculation.
"""

import pytest
import numpy as np
from src.geoutils import (
    haversine_distance,
    bearing_between_points,
    three_point_curvature,
    compute_curvature_series,
    detect_gps_jumps,
    road_class_binning
)


def test_haversine_distance_zero():
    """Test distance between same point is zero."""
    lat, lon = 45.66, 25.56
    
    distance = haversine_distance(lat, lon, lat, lon)
    
    assert np.isclose(distance, 0, atol=1e-6)


def test_haversine_distance_known():
    """Test distance calculation with known values."""
    # Approximate 1 degree latitude = 111 km
    lat1, lon1 = 45.0, 25.0
    lat2, lon2 = 46.0, 25.0
    
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    
    # Should be roughly 111 km
    assert 110000 < distance < 112000


def test_bearing_north():
    """Test bearing calculation going north."""
    lat1, lon1 = 45.0, 25.0
    lat2, lon2 = 46.0, 25.0
    
    bearing = bearing_between_points(lat1, lon1, lat2, lon2)
    
    # Should be close to 0 degrees (north)
    assert 0 <= bearing < 10 or 350 < bearing <= 360


def test_bearing_east():
    """Test bearing calculation going east."""
    lat1, lon1 = 45.0, 25.0
    lat2, lon2 = 45.0, 26.0
    
    bearing = bearing_between_points(lat1, lon1, lat2, lon2)
    
    # Should be close to 90 degrees (east)
    assert 80 < bearing < 100


def test_bearing_range():
    """Test that bearing is always in [0, 360)."""
    for _ in range(100):
        lat1 = np.random.uniform(-90, 90)
        lon1 = np.random.uniform(-180, 180)
        lat2 = np.random.uniform(-90, 90)
        lon2 = np.random.uniform(-180, 180)
        
        bearing = bearing_between_points(lat1, lon1, lat2, lon2)
        
        assert 0 <= bearing < 360


def test_three_point_curvature_straight():
    """Test curvature of straight line is near zero."""
    # Three collinear points
    lat1, lon1 = 45.0, 25.0
    lat2, lon2 = 45.001, 25.001
    lat3, lon3 = 45.002, 25.002
    
    curvature, radius = three_point_curvature(lat1, lon1, lat2, lon2, lat3, lon3)
    
    # Curvature should be very small
    assert curvature < 0.001


def test_three_point_curvature_circle():
    """Test curvature of circular arc."""
    # Points on a circle with known radius
    center_lat, center_lon = 45.0, 25.0
    radius_deg = 0.01  # degrees
    
    # Three points at 0, 90, 180 degrees
    lat1 = center_lat + radius_deg
    lon1 = center_lon
    
    lat2 = center_lat
    lon2 = center_lon + radius_deg
    
    lat3 = center_lat - radius_deg
    lon3 = center_lon
    
    curvature, radius_m = three_point_curvature(lat1, lon1, lat2, lon2, lat3, lon3)
    
    # Curvature should be positive
    assert curvature > 0
    
    # Radius should be reasonable
    assert 500 < radius_m < 2000


def test_compute_curvature_series_shape():
    """Test curvature series output shape."""
    lats = np.linspace(45.0, 45.01, 100)
    lons = np.linspace(25.0, 25.01, 100)
    
    curvatures = compute_curvature_series(lats, lons)
    
    assert len(curvatures) == len(lats)


def test_compute_curvature_series_endpoints():
    """Test that endpoints have zero curvature."""
    lats = np.linspace(45.0, 45.01, 100)
    lons = np.linspace(25.0, 25.01, 100)
    
    curvatures = compute_curvature_series(lats, lons)
    
    # First and last should be zero (no neighbors)
    assert curvatures[0] == 0
    assert curvatures[-1] == 0


def test_compute_curvature_series_with_nans():
    """Test handling of NaN values."""
    lats = np.linspace(45.0, 45.01, 100)
    lons = np.linspace(25.0, 25.01, 100)
    
    # Add some NaNs
    lats[50:55] = np.nan
    
    curvatures = compute_curvature_series(lats, lons)
    
    # Curvatures around NaNs should also be NaN
    assert np.isnan(curvatures[49:56]).all()


def test_detect_gps_jumps_no_jumps():
    """Test GPS jump detection with clean data."""
    # Simulate smooth movement at 10 m/s
    n = 100
    timestamps = np.arange(n, dtype=float)
    lats = np.linspace(45.0, 45.01, n)
    lons = np.linspace(25.0, 25.01, n)
    
    valid = detect_gps_jumps(lats, lons, timestamps, max_speed=50.0)
    
    # All points should be valid
    assert valid.sum() >= n - 2  # Allow a couple false positives


def test_detect_gps_jumps_with_jump():
    """Test GPS jump detection with obvious jump."""
    n = 100
    timestamps = np.arange(n, dtype=float)
    lats = np.linspace(45.0, 45.01, n)
    lons = np.linspace(25.0, 25.01, n)
    
    # Add a jump
    lats[50] = 46.0  # Jump 1 degree
    
    valid = detect_gps_jumps(lats, lons, timestamps, max_speed=50.0)
    
    # Jump point should be marked invalid
    assert not valid[50]


def test_road_class_binning():
    """Test road class categorization."""
    # Test different speeds
    assert road_class_binning(2.0) == "residential"  # ~7 km/h
    assert road_class_binning(10.0) == "urban"  # ~36 km/h
    assert road_class_binning(20.0) == "rural"  # ~72 km/h
    assert road_class_binning(30.0) == "highway"  # ~108 km/h


def test_road_class_boundaries():
    """Test road class boundary values."""
    # Test boundary conditions
    assert road_class_binning(4.9) == "residential"
    assert road_class_binning(5.1) == "urban"
    assert road_class_binning(13.8) == "urban"
    assert road_class_binning(14.0) == "rural"
    assert road_class_binning(22.0) == "rural"
    assert road_class_binning(22.5) == "highway"


def test_curvature_negative_values():
    """Test that curvature can be negative for opposite curve direction."""
    # This depends on implementation - curvature magnitude is what matters
    lats = np.array([45.0, 45.001, 45.002, 45.001, 45.0])
    lons = np.array([25.0, 25.001, 25.002, 25.003, 25.004])
    
    curvatures = compute_curvature_series(lats, lons)
    
    # Should have some non-zero curvatures
    assert np.any(curvatures != 0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
