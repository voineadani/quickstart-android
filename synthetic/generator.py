"""
Synthetic driving data generator for testing the pipeline.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import argparse


def generate_straight_driving(duration_s: float, sampling_rate: float = 100.0) -> dict:
    """Generate straight driving segment."""
    n_samples = int(duration_s * sampling_rate)
    t = np.linspace(0, duration_s, n_samples)
    
    # Constant acceleration in forward direction
    accX = np.random.normal(0, 0.5, n_samples)
    accY = np.random.normal(9.81, 0.3, n_samples)  # Gravity + small noise
    accZ = np.random.normal(0, 0.3, n_samples)
    
    # Minimal rotation
    gyroX = np.random.normal(0, 0.05, n_samples)
    gyroY = np.random.normal(0, 0.05, n_samples)
    gyroZ = np.random.normal(0, 0.05, n_samples)
    
    return {
        "accX": accX, "accY": accY, "accZ": accZ,
        "gyroX": gyroX, "gyroY": gyroY, "gyroZ": gyroZ,
        "t": t
    }


def generate_turn(duration_s: float, direction: str = "left",
                 sampling_rate: float = 100.0) -> dict:
    """Generate turn segment."""
    n_samples = int(duration_s * sampling_rate)
    t = np.linspace(0, duration_s, n_samples)
    
    # Centripetal acceleration
    turn_accel = 2.0  # m/s^2
    yaw_rate = 0.5 if direction == "left" else -0.5  # rad/s
    
    accX = np.random.normal(turn_accel, 0.5, n_samples)
    accY = np.random.normal(9.81, 0.3, n_samples)
    accZ = np.random.normal(0, 0.3, n_samples)
    
    gyroX = np.random.normal(0, 0.1, n_samples)
    gyroY = np.random.normal(0, 0.1, n_samples)
    gyroZ = np.random.normal(yaw_rate, 0.1, n_samples)
    
    return {
        "accX": accX, "accY": accY, "accZ": accZ,
        "gyroX": gyroX, "gyroY": gyroY, "gyroZ": gyroZ,
        "t": t
    }


def generate_brake(duration_s: float, harsh: bool = False,
                  sampling_rate: float = 100.0) -> dict:
    """Generate braking segment."""
    n_samples = int(duration_s * sampling_rate)
    t = np.linspace(0, duration_s, n_samples)
    
    # Deceleration
    decel = -5.0 if harsh else -2.0  # m/s^2
    
    # Ramp deceleration
    accX_ramp = np.linspace(0, decel, n_samples) + np.random.normal(0, 0.3, n_samples)
    
    accX = accX_ramp
    accY = np.random.normal(9.81, 0.3, n_samples)
    accZ = np.random.normal(0, 0.3, n_samples)
    
    gyroX = np.random.normal(0, 0.1, n_samples)
    gyroY = np.random.normal(0, 0.1, n_samples)
    gyroZ = np.random.normal(0, 0.05, n_samples)
    
    return {
        "accX": accX, "accY": accY, "accZ": accZ,
        "gyroX": gyroX, "gyroY": gyroY, "gyroZ": gyroZ,
        "t": t
    }


def generate_gps_trace(start_lat: float, start_lon: float,
                      maneuvers: list, sampling_rate: float = 1.0) -> dict:
    """Generate GPS trace for maneuvers."""
    total_duration = sum(m["duration"] for m in maneuvers)
    n_samples = int(total_duration * sampling_rate)
    
    lats = np.zeros(n_samples)
    lons = np.zeros(n_samples)
    speeds = np.zeros(n_samples)
    bearings = np.zeros(n_samples)
    
    # Current position and bearing
    lat, lon = start_lat, start_lon
    bearing = 45.0  # degrees
    speed = 15.0  # m/s (54 km/h)
    
    idx = 0
    for maneuver in maneuvers:
        duration = maneuver["duration"]
        n_seg = int(duration * sampling_rate)
        
        if maneuver["type"] == "straight":
            # Move forward
            for i in range(n_seg):
                lat += (speed / 111000) * np.cos(np.radians(bearing)) / sampling_rate
                lon += (speed / (111000 * np.cos(np.radians(lat)))) * np.sin(np.radians(bearing)) / sampling_rate
                
                if idx < n_samples:
                    lats[idx] = lat
                    lons[idx] = lon
                    speeds[idx] = speed
                    bearings[idx] = bearing
                    idx += 1
        
        elif maneuver["type"] in ["left_turn", "right_turn"]:
            # Turn
            angle_change = 90 if maneuver["type"] == "left_turn" else -90
            bearing_step = angle_change / n_seg
            
            for i in range(n_seg):
                bearing += bearing_step
                bearing = bearing % 360
                
                lat += (speed / 111000) * np.cos(np.radians(bearing)) / sampling_rate
                lon += (speed / (111000 * np.cos(np.radians(lat)))) * np.sin(np.radians(bearing)) / sampling_rate
                
                if idx < n_samples:
                    lats[idx] = lat
                    lons[idx] = lon
                    speeds[idx] = speed
                    bearings[idx] = bearing
                    idx += 1
        
        elif "brake" in maneuver["type"]:
            # Decelerate
            speed_step = -speed / n_seg
            
            for i in range(n_seg):
                speed = max(0, speed + speed_step)
                
                lat += (speed / 111000) * np.cos(np.radians(bearing)) / sampling_rate
                lon += (speed / (111000 * np.cos(np.radians(lat)))) * np.sin(np.radians(bearing)) / sampling_rate
                
                if idx < n_samples:
                    lats[idx] = lat
                    lons[idx] = lon
                    speeds[idx] = speed
                    bearings[idx] = bearing
                    idx += 1
            
            speed = 15.0  # Reset speed
    
    return {
        "lat": lats,
        "lon": lons,
        "speed": speeds,
        "bearing": bearings
    }


def generate_trip(output_path: Path, start_time: datetime,
                 start_lat: float = 45.66, start_lon: float = 25.56):
    """Generate a complete synthetic trip."""
    sampling_rate_imu = 100.0
    sampling_rate_gps = 1.0
    
    # Define maneuver sequence
    maneuvers = [
        {"type": "straight", "duration": 10.0},
        {"type": "left_turn", "duration": 3.0},
        {"type": "straight", "duration": 15.0},
        {"type": "right_turn", "duration": 3.0},
        {"type": "straight", "duration": 10.0},
        {"type": "harsh_brake", "duration": 2.0},
        {"type": "straight", "duration": 10.0},
    ]
    
    # Generate IMU data
    all_imu = []
    for maneuver in maneuvers:
        if maneuver["type"] == "straight":
            data = generate_straight_driving(maneuver["duration"], sampling_rate_imu)
        elif "turn" in maneuver["type"]:
            direction = "left" if "left" in maneuver["type"] else "right"
            data = generate_turn(maneuver["duration"], direction, sampling_rate_imu)
        elif "brake" in maneuver["type"]:
            harsh = "harsh" in maneuver["type"]
            data = generate_brake(maneuver["duration"], harsh, sampling_rate_imu)
        
        all_imu.append(data)
    
    # Concatenate IMU
    imu_data = {
        key: np.concatenate([seg[key] for seg in all_imu])
        for key in ["accX", "accY", "accZ", "gyroX", "gyroY", "gyroZ"]
    }
    
    # Generate GPS
    gps_data = generate_gps_trace(start_lat, start_lon, maneuvers, sampling_rate_gps)
    
    # Create DataFrame
    n_imu = len(imu_data["accX"])
    n_gps = len(gps_data["lat"])
    
    # Upsample GPS to match IMU rate
    gps_indices = np.linspace(0, n_gps-1, n_imu).astype(int)
    
    df = pd.DataFrame({
        "timestamp": [start_time + timedelta(seconds=i/sampling_rate_imu) for i in range(n_imu)],
        "elapsed": np.arange(n_imu) / sampling_rate_imu,
        "accX": imu_data["accX"],
        "accY": imu_data["accY"],
        "accZ": imu_data["accZ"],
        "gyroX": imu_data["gyroX"],
        "gyroY": imu_data["gyroY"],
        "gyroZ": imu_data["gyroZ"],
        "lat": gps_data["lat"][gps_indices],
        "lon": gps_data["lon"][gps_indices],
        "speed": gps_data["speed"][gps_indices],
        "bearing": gps_data["bearing"][gps_indices],
        "accuracy": np.random.uniform(5, 15, n_imu),
    })
    
    # Save
    df.to_csv(output_path, index=False)
    print(f"Generated trip with {len(df)} samples, saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default="./data/synthetic_trip.csv")
    parser.add_argument("--n_trips", type=int, default=3)
    args = parser.parse_args()
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate multiple trips
    start_time = datetime(2025, 6, 6, 19, 0, 0)
    
    for i in range(args.n_trips):
        trip_output = output_path.parent / f"synthetic_trip_{i}.csv"
        trip_start = start_time + timedelta(hours=i)
        
        generate_trip(trip_output, trip_start)
    
    print(f"Generated {args.n_trips} synthetic trips")
