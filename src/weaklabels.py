"""
Weak label generation from physics-based rules.
"""

import numpy as np
import pandas as pd
from typing import Dict, List
import logging
from . import geoutils

logger = logging.getLogger(__name__)


class WeakLabeler:
    """Generate weak labels from sensor physics and GPS."""
    
    def __init__(self, config: Dict):
        thresholds = config.get("thresholds", {})
        
        # Thresholds
        self.harsh_brake_jerk = thresholds.get("harsh_brake_jerk", -3.0)
        self.harsh_accel_jerk = thresholds.get("harsh_accel_jerk", 3.0)
        self.left_turn_yaw = thresholds.get("left_turn_yaw", 0.3)
        self.right_turn_yaw = thresholds.get("right_turn_yaw", -0.3)
        self.emergency_brake_dv = thresholds.get("emergency_brake_dv", -5.0)
        self.sharp_curve_curvature = thresholds.get("sharp_curve_curvature", 0.02)
        
        # Roundabout detection
        ra_config = thresholds.get("roundabout", {})
        self.ra_min_duration = ra_config.get("min_duration", 3.0)
        self.ra_min_angle = ra_config.get("min_total_angle", 270)
        self.ra_max_radius = ra_config.get("max_radius", 50)
        
        # GPS
        gps_config = config.get("gps", {})
        self.min_accuracy = gps_config.get("min_accuracy", 20)
        self.min_speed_for_bearing = gps_config.get("min_speed_for_bearing", 1.0)
        
    def compute_jerk(self, accel: np.ndarray, dt: float = 0.01) -> np.ndarray:
        """Compute jerk (derivative of acceleration)."""
        jerk = np.gradient(accel, dt)
        return jerk
    
    def compute_yaw_rate(self, gyro_z: np.ndarray) -> np.ndarray:
        """Yaw rate is directly from gyroscope Z."""
        return gyro_z
    
    def compute_delta_v(self, speed: np.ndarray, dt: float = 1.0) -> np.ndarray:
        """Compute change in velocity."""
        delta_v = np.diff(speed, prepend=speed[0]) / dt
        return delta_v
    
    def label_harsh_events(self, df: pd.DataFrame, sampling_rate: float = 100.0) -> pd.DataFrame:
        """Label harsh braking and acceleration."""
        df = df.copy()
        dt = 1.0 / sampling_rate
        
        # Initialize labels
        df["harsh_brake"] = False
        df["harsh_accel"] = False
        
        # Compute jerk from linear acceleration
        if "linear_X" in df.columns:
            jerk = self.compute_jerk(df["linear_X"].fillna(0).values, dt)
            
            df.loc[jerk < self.harsh_brake_jerk, "harsh_brake"] = True
            df.loc[jerk > self.harsh_accel_jerk, "harsh_accel"] = True
            
            logger.info(f"Harsh brakes: {df['harsh_brake'].sum()}, "
                       f"harsh accel: {df['harsh_accel'].sum()}")
        
        return df
    
    def label_turns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Label left and right turns from yaw rate."""
        df = df.copy()
        
        df["left_turn"] = False
        df["right_turn"] = False
        
        if "gyroZ" in df.columns:
            yaw_rate = self.compute_yaw_rate(df["gyroZ"].fillna(0).values)
            
            df.loc[yaw_rate > self.left_turn_yaw, "left_turn"] = True
            df.loc[yaw_rate < self.right_turn_yaw, "right_turn"] = True
            
            logger.info(f"Left turns: {df['left_turn'].sum()}, "
                       f"right turns: {df['right_turn'].sum()}")
        
        return df
    
    def label_emergency_brake(self, df: pd.DataFrame) -> pd.DataFrame:
        """Label emergency braking from speed change."""
        df = df.copy()
        df["emergency_brake"] = False
        
        if "speed" in df.columns:
            delta_v = self.compute_delta_v(df["speed"].fillna(0).values)
            
            df.loc[delta_v < self.emergency_brake_dv, "emergency_brake"] = True
            
            logger.info(f"Emergency brakes: {df['emergency_brake'].sum()}")
        
        return df
    
    def label_curves(self, df: pd.DataFrame) -> pd.DataFrame:
        """Label sharp curves from GPS curvature."""
        df = df.copy()
        df["sharp_curve"] = False
        
        if all(col in df.columns for col in ["lat", "lon"]):
            lats = df["lat"].values
            lons = df["lon"].values
            
            accuracies = df["accuracy"].values if "accuracy" in df.columns else None
            
            curvatures = geoutils.compute_curvature_series(
                lats, lons, 
                min_accuracy=self.min_accuracy,
                accuracies=accuracies
            )
            
            df["curvature"] = curvatures
            df.loc[np.abs(curvatures) > self.sharp_curve_curvature, "sharp_curve"] = True
            
            logger.info(f"Sharp curves: {df['sharp_curve'].sum()}")
        
        return df
    
    def detect_roundabouts(self, df: pd.DataFrame, sampling_rate: float = 1.0) -> pd.DataFrame:
        """Detect roundabouts from GPS pattern."""
        df = df.copy()
        df["roundabout"] = False
        
        if not all(col in df.columns for col in ["lat", "lon", "speed"]):
            return df
        
        # Look for circular patterns
        window_size = int(self.ra_min_duration * sampling_rate)
        
        for i in range(len(df) - window_size):
            window = df.iloc[i:i+window_size]
            
            # Check if speed is consistent (not stopping)
            if window["speed"].mean() < self.min_speed_for_bearing:
                continue
            
            # Calculate total angle change
            lats = window["lat"].values
            lons = window["lon"].values
            
            if np.isnan(lats).any() or np.isnan(lons).any():
                continue
            
            # Compute bearings
            bearings = []
            for j in range(len(lats) - 1):
                bearing = geoutils.bearing_between_points(
                    lats[j], lons[j], lats[j+1], lons[j+1]
                )
                bearings.append(bearing)
            
            if len(bearings) < 2:
                continue
            
            # Total angle change
            total_angle = 0
            for j in range(len(bearings) - 1):
                angle_diff = bearings[j+1] - bearings[j]
                # Handle wraparound
                if angle_diff > 180:
                    angle_diff -= 360
                elif angle_diff < -180:
                    angle_diff += 360
                total_angle += abs(angle_diff)
            
            # Check roundabout criteria
            if total_angle > self.ra_min_angle:
                # Estimate radius
                if len(lats) > 2:
                    _, radius = geoutils.three_point_curvature(
                        lats[0], lons[0],
                        lats[len(lats)//2], lons[len(lons)//2],
                        lats[-1], lons[-1]
                    )
                    
                    if radius < self.ra_max_radius:
                        df.loc[i:i+window_size, "roundabout"] = True
        
        logger.info(f"Roundabout segments: {df['roundabout'].sum()}")
        
        return df
    
    def generate_all_labels(self, df: pd.DataFrame, 
                          sampling_rate: float = 100.0) -> pd.DataFrame:
        """Generate all weak labels."""
        logger.info("Generating weak labels...")
        
        df = self.label_harsh_events(df, sampling_rate)
        df = self.label_turns(df)
        df = self.label_emergency_brake(df)
        df = self.label_curves(df)
        df = self.detect_roundabouts(df, sampling_rate=1.0)
        
        return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    from dataio import load_config, DataLoader
    from preprocessing import Preprocessor
    
    config = load_config("./configs/weaklabels.yml")
    dataset_config = load_config("./configs/dataset.yml")
    
    labeler = WeakLabeler(config)
    
    loader = DataLoader("./configs/dataset.yml")
    preprocessor = Preprocessor(dataset_config)
    
    dfs = loader.load_all()
    
    if dfs:
        df = dfs[0]
        df_processed, _ = preprocessor.preprocess_pipeline(df)
        
        df_labeled = labeler.generate_all_labels(df_processed)
        
        print(f"Labeled shape: {df_labeled.shape}")
        print(f"Label columns: {[c for c in df_labeled.columns if 'harsh' in c or 'turn' in c or 'curve' in c]}")
        
        # Statistics
        for col in ["harsh_brake", "harsh_accel", "left_turn", "right_turn", 
                   "emergency_brake", "sharp_curve", "roundabout"]:
            if col in df_labeled.columns:
                print(f"{col}: {df_labeled[col].sum()} ({df_labeled[col].sum()/len(df_labeled)*100:.2f}%)")
