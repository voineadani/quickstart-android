"""
Preprocessing: resampling, gap interpolation, gravity split, pose handling, standardization.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from scipy import interpolate, signal
from scipy.spatial.transform import Rotation
import logging

logger = logging.getLogger(__name__)


class Preprocessor:
    """Preprocess sensor data."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.imu_rate = config.get("sampling_rates", {}).get("imu", 100)
        self.gps_rate = config.get("sampling_rates", {}).get("gps", 1)
        
    def resample(self, df: pd.DataFrame, target_rate: float, 
                channels: List[str]) -> pd.DataFrame:
        """Resample data to target rate."""
        if "timestamp" not in df.columns:
            raise ValueError("timestamp column required for resampling")
        
        # Convert to datetime if needed
        timestamps = pd.to_datetime(df["timestamp"])
        df = df.copy()
        df["timestamp"] = timestamps
        df = df.set_index("timestamp")
        
        # Create uniform time grid
        start_time = timestamps.min()
        end_time = timestamps.max()
        duration = (end_time - start_time).total_seconds()
        
        n_samples = int(duration * target_rate)
        uniform_times = pd.date_range(start=start_time, end=end_time, periods=n_samples)
        
        # Resample each channel
        resampled = pd.DataFrame(index=uniform_times)
        
        for channel in channels:
            if channel in df.columns:
                # Linear interpolation for continuous signals
                resampled[channel] = df[channel].reindex(
                    uniform_times, method=None
                ).interpolate(method="linear", limit=int(target_rate * 2))
        
        resampled.index.name = "timestamp"
        resampled = resampled.reset_index()
        
        logger.info(f"Resampled from {len(df)} to {len(resampled)} samples at {target_rate} Hz")
        return resampled
    
    def interpolate_gaps(self, df: pd.DataFrame, channels: List[str], 
                        max_gap: float = 1.0) -> pd.DataFrame:
        """Interpolate small gaps in data."""
        df = df.copy()
        
        for channel in channels:
            if channel not in df.columns:
                continue
            
            # Find gaps
            mask = df[channel].notna()
            gap_starts = np.where(~mask[:-1] & mask[1:])[0] + 1
            gap_ends = np.where(mask[:-1] & ~mask[1:])[0]
            
            # Interpolate small gaps
            for start, end in zip(gap_starts, gap_ends):
                gap_size = end - start + 1
                if gap_size <= max_gap * self.imu_rate:  # Convert seconds to samples
                    df[channel].iloc[start:end+1] = df[channel].iloc[start:end+1].interpolate(
                        method="linear"
                    )
        
        return df
    
    def split_gravity(self, df: pd.DataFrame, 
                     acc_channels: List[str] = ["accX", "accY", "accZ"],
                     cutoff_freq: float = 0.3) -> pd.DataFrame:
        """Split acceleration into gravity and linear components."""
        df = df.copy()
        
        # Low-pass filter for gravity
        sos = signal.butter(4, cutoff_freq, btype="low", fs=self.imu_rate, output="sos")
        
        for i, channel in enumerate(acc_channels):
            if channel not in df.columns:
                continue
            
            acc_data = df[channel].fillna(method="ffill").fillna(method="bfill").values
            
            # Gravity component (low-pass)
            gravity = signal.sosfilt(sos, acc_data)
            
            # Linear acceleration (high-pass)
            linear = acc_data - gravity
            
            # Store results
            df[f"gravity_{channel[-1]}"] = gravity
            df[f"linear_{channel[-1]}"] = linear
        
        logger.info("Split acceleration into gravity and linear components")
        return df
    
    def rotate_to_vehicle_frame(self, df: pd.DataFrame, 
                                acc_channels: List[str] = ["accX", "accY", "accZ"],
                                gyro_channels: List[str] = ["gyroX", "gyroY", "gyroZ"],
                                use_quaternion: bool = True) -> pd.DataFrame:
        """Rotate sensors to vehicle frame using orientation data."""
        df = df.copy()
        
        if use_quaternion and all(q in df.columns for q in ["qx", "qy", "qz", "qw"]):
            # Use quaternion orientation
            for i in range(len(df)):
                q = [df.loc[i, "qx"], df.loc[i, "qy"], df.loc[i, "qz"], df.loc[i, "qw"]]
                
                # Skip invalid quaternions
                if any(pd.isna(q)) or np.allclose(q, [0, 0, 0, 1]):
                    continue
                
                rot = Rotation.from_quat(q)
                
                # Rotate acceleration
                if all(ch in df.columns for ch in acc_channels):
                    acc_vec = [df.loc[i, ch] for ch in acc_channels]
                    if not any(pd.isna(acc_vec)):
                        acc_rotated = rot.apply(acc_vec, inverse=True)
                        for j, ch in enumerate(acc_channels):
                            df.loc[i, f"vehicle_{ch}"] = acc_rotated[j]
                
                # Rotate gyroscope
                if all(ch in df.columns for ch in gyro_channels):
                    gyro_vec = [df.loc[i, ch] for ch in gyro_channels]
                    if not any(pd.isna(gyro_vec)):
                        gyro_rotated = rot.apply(gyro_vec, inverse=True)
                        for j, ch in enumerate(gyro_channels):
                            df.loc[i, f"vehicle_{ch}"] = gyro_rotated[j]
            
            logger.info("Rotated to vehicle frame using quaternions")
        
        else:
            logger.warning("Quaternion data not available, skipping rotation")
        
        return df
    
    def apply_random_rotation(self, data: np.ndarray, 
                            max_angle_deg: float = 15.0) -> np.ndarray:
        """Apply random 3D rotation for augmentation."""
        # Generate random rotation
        angles = np.random.uniform(-max_angle_deg, max_angle_deg, size=3)
        rot = Rotation.from_euler("xyz", angles, degrees=True)
        
        # Apply to each time step
        if data.shape[1] == 3:
            return rot.apply(data)
        else:
            # Apply to each 3D vector in data
            rotated = data.copy()
            for i in range(0, data.shape[1], 3):
                if i + 3 <= data.shape[1]:
                    rotated[:, i:i+3] = rot.apply(data[:, i:i+3])
            return rotated
    
    def standardize(self, df: pd.DataFrame, channels: List[str],
                   per_device: bool = False) -> Tuple[pd.DataFrame, Dict]:
        """Standardize channels (z-score normalization)."""
        df = df.copy()
        stats = {}
        
        if per_device and "device_id" in df.columns:
            # Per-device standardization
            for device in df["device_id"].unique():
                mask = df["device_id"] == device
                device_stats = {}
                
                for channel in channels:
                    if channel not in df.columns:
                        continue
                    
                    data = df.loc[mask, channel]
                    mean = data.mean()
                    std = data.std()
                    
                    if std > 0:
                        df.loc[mask, f"{channel}_norm"] = (data - mean) / std
                        device_stats[channel] = {"mean": float(mean), "std": float(std)}
                
                stats[str(device)] = device_stats
        
        else:
            # Global standardization
            for channel in channels:
                if channel not in df.columns:
                    continue
                
                mean = df[channel].mean()
                std = df[channel].std()
                
                if std > 0:
                    df[f"{channel}_norm"] = (df[channel] - mean) / std
                    stats[channel] = {"mean": float(mean), "std": float(std)}
        
        logger.info(f"Standardized {len(channels)} channels")
        return df, stats
    
    def preprocess_pipeline(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Run complete preprocessing pipeline."""
        metadata = {}
        
        # 1. Resample IMU
        imu_channels = ["accX", "accY", "accZ", "gyroX", "gyroY", "gyroZ"]
        df = self.resample(df, self.imu_rate, imu_channels)
        
        # 2. Interpolate small gaps
        df = self.interpolate_gaps(df, imu_channels, max_gap=1.0)
        
        # 3. Split gravity
        df = self.split_gravity(df)
        
        # 4. Standardize
        df, stats = self.standardize(df, imu_channels + ["speed"])
        metadata["normalization_stats"] = stats
        
        logger.info("Preprocessing pipeline complete")
        return df, metadata


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    from dataio import load_config, DataLoader
    
    config = load_config("./configs/dataset.yml")
    preprocessor = Preprocessor(config)
    
    loader = DataLoader("./configs/dataset.yml")
    dfs = loader.load_all()
    
    if dfs:
        df = dfs[0]
        df_processed, metadata = preprocessor.preprocess_pipeline(df)
        
        print(f"Original shape: {dfs[0].shape}")
        print(f"Processed shape: {df_processed.shape}")
        print(f"New columns: {[c for c in df_processed.columns if c not in dfs[0].columns]}")
