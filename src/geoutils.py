"""
Geospatial utilities: map-free curvature, GPS drift guards, coordinate transformations.
"""

import numpy as np
from typing import Tuple, List, Optional
import logging

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great circle distance between two points.
    
    Returns:
        Distance in meters
    """
    R = 6371000  # Earth radius in meters
    
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c


def bearing_between_points(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate bearing from point 1 to point 2.
    
    Returns:
        Bearing in degrees (0-360)
    """
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    
    x = np.sin(dlon) * np.cos(lat2)
    y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
    
    bearing = np.arctan2(x, y)
    bearing = np.degrees(bearing)
    bearing = (bearing + 360) % 360
    
    return bearing


def three_point_curvature(lat1: float, lon1: float,
                         lat2: float, lon2: float,
                         lat3: float, lon3: float) -> Tuple[float, float]:
    """
    Calculate curvature from three GPS points using circumcircle.
    
    Returns:
        curvature (1/meters), radius (meters)
    """
    # Convert to local Cartesian coordinates (approximate)
    lat_center = (lat1 + lat2 + lat3) / 3
    lon_center = (lon1 + lon2 + lon3) / 3
    
    # Meters per degree at center
    m_per_deg_lat = 111132.92 - 559.82 * np.cos(2 * np.radians(lat_center))
    m_per_deg_lon = 111412.84 * np.cos(np.radians(lat_center))
    
    # Convert to meters
    x1 = (lon1 - lon_center) * m_per_deg_lon
    y1 = (lat1 - lat_center) * m_per_deg_lat
    x2 = (lon2 - lon_center) * m_per_deg_lon
    y2 = (lat2 - lat_center) * m_per_deg_lat
    x3 = (lon3 - lon_center) * m_per_deg_lon
    y3 = (lat3 - lat_center) * m_per_deg_lat
    
    # Calculate circumcircle
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    
    if abs(d) < 1e-6:  # Nearly collinear
        return 0.0, np.inf
    
    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + 
          (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + 
          (x3**2 + y3**2) * (x2 - x1)) / d
    
    radius = np.sqrt((x1 - ux)**2 + (y1 - uy)**2)
    
    if radius < 1e-6:
        return np.inf, 0.0
    
    curvature = 1.0 / radius
    
    return curvature, radius


def compute_curvature_series(lats: np.ndarray, lons: np.ndarray,
                            min_accuracy: float = 20.0,
                            accuracies: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Compute curvature for a series of GPS points.
    
    Args:
        lats, lons: GPS coordinates
        min_accuracy: Minimum GPS accuracy in meters
        accuracies: Optional GPS accuracy values
        
    Returns:
        Array of curvatures (1/m)
    """
    n = len(lats)
    curvatures = np.zeros(n)
    
    for i in range(1, n-1):
        # Check accuracy
        if accuracies is not None:
            if (accuracies[i-1] > min_accuracy or 
                accuracies[i] > min_accuracy or 
                accuracies[i+1] > min_accuracy):
                curvatures[i] = np.nan
                continue
        
        # Check for NaN
        if (np.isnan(lats[i-1:i+2]).any() or np.isnan(lons[i-1:i+2]).any()):
            curvatures[i] = np.nan
            continue
        
        try:
            curvature, _ = three_point_curvature(
                lats[i-1], lons[i-1],
                lats[i], lons[i],
                lats[i+1], lons[i+1]
            )
            curvatures[i] = curvature
        except:
            curvatures[i] = np.nan
    
    return curvatures


def detect_gps_jumps(lats: np.ndarray, lons: np.ndarray, 
                    timestamps: np.ndarray,
                    max_speed: float = 50.0) -> np.ndarray:
    """
    Detect unrealistic GPS jumps (drift/errors).
    
    Args:
        lats, lons: GPS coordinates
        timestamps: Timestamps in seconds
        max_speed: Maximum realistic speed in m/s
        
    Returns:
        Boolean mask (True = valid point)
    """
    n = len(lats)
    valid = np.ones(n, dtype=bool)
    
    for i in range(1, n):
        dt = timestamps[i] - timestamps[i-1]
        
        if dt <= 0 or dt > 10:  # Skip invalid time differences
            valid[i] = False
            continue
        
        distance = haversine_distance(
            lats[i-1], lons[i-1],
            lats[i], lons[i]
        )
        
        speed = distance / dt
        
        if speed > max_speed:
            valid[i] = False
            logger.debug(f"GPS jump detected at index {i}: speed={speed:.1f} m/s")
    
    return valid


def road_class_binning(speed: float) -> str:
    """
    Approximate road class from speed.
    
    Args:
        speed: Speed in m/s
        
    Returns:
        Road class string
    """
    if speed < 5.0:  # < 18 km/h
        return "residential"
    elif speed < 13.9:  # < 50 km/h
        return "urban"
    elif speed < 22.2:  # < 80 km/h
        return "rural"
    else:
        return "highway"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test distance and bearing
    lat1, lon1 = 45.6624762, 25.5674916
    lat2, lon2 = 45.6625, 25.5675
    
    dist = haversine_distance(lat1, lon1, lat2, lon2)
    bearing = bearing_between_points(lat1, lon1, lat2, lon2)
    
    print(f"Distance: {dist:.2f} m")
    print(f"Bearing: {bearing:.1f} degrees")
    
    # Test curvature
    lat3, lon3 = 45.6626, 25.5676
    curvature, radius = three_point_curvature(lat1, lon1, lat2, lon2, lat3, lon3)
    
    print(f"Curvature: {curvature:.6f} 1/m")
    print(f"Radius: {radius:.2f} m")
    
    # Test series
    lats = np.array([45.6624, 45.6625, 45.6626, 45.6627, 45.6628])
    lons = np.array([25.5674, 25.5675, 25.5676, 25.5677, 25.5678])
    
    curvatures = compute_curvature_series(lats, lons)
    print(f"Curvature series: {curvatures}")
    
    # Test GPS jump detection
    timestamps = np.array([0, 1, 2, 3, 4], dtype=float)
    valid = detect_gps_jumps(lats, lons, timestamps)
    print(f"Valid GPS points: {valid}")
