"""
Segmentation: windowing and Bayesian Online Changepoint Detection.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class BayesianOnlineChangepoint:
    """Bayesian Online Changepoint Detection for refining segment boundaries."""
    
    def __init__(self, hazard_rate: float = 0.01, delay: int = 15):
        """
        Args:
            hazard_rate: Prior probability of changepoint at each timestep
            delay: Delay for better change detection
        """
        self.hazard_rate = hazard_rate
        self.delay = delay
        
    def _gaussian_obs_log_likelihood(self, data: np.ndarray, 
                                    t: int, s: int) -> float:
        """Compute Gaussian observation log likelihood."""
        if s < 1:
            return 0.0
        
        # Use data from s to t
        segment = data[max(0, t-s):t+1]
        
        if len(segment) < 2:
            return 0.0
        
        mean = np.mean(segment)
        var = np.var(segment) + 1e-6
        
        # Log likelihood for current observation
        obs = data[t]
        log_lik = -0.5 * np.log(2 * np.pi * var) - 0.5 * ((obs - mean) ** 2) / var
        
        return log_lik
    
    def detect(self, data: np.ndarray, threshold: float = 0.5) -> List[int]:
        """
        Detect changepoints in time series data.
        
        Args:
            data: 1D time series
            threshold: Threshold for changepoint probability
            
        Returns:
            List of changepoint indices
        """
        n = len(data)
        
        # Initialize run length distribution
        R = np.zeros((n, n))
        R[0, 0] = 1.0
        
        changepoints = []
        
        for t in range(1, n):
            # Evaluate predictive probability
            pred_probs = np.zeros(t + 1)
            
            for s in range(t + 1):
                if R[t-1, s] > 0:
                    pred_probs[s] = np.exp(
                        self._gaussian_obs_log_likelihood(data, t, s)
                    )
            
            # Calculate growth probabilities
            growth_probs = R[t-1, :t] * pred_probs[:t] * (1 - self.hazard_rate)
            
            # Calculate changepoint probability
            cp_prob = np.sum(R[t-1, :t] * pred_probs[:t] * self.hazard_rate)
            
            # Update run length distribution
            R[t, 0] = cp_prob
            R[t, 1:t+1] = growth_probs
            
            # Normalize
            total = np.sum(R[t, :t+1])
            if total > 0:
                R[t, :t+1] /= total
            
            # Detect changepoint
            if R[t, 0] > threshold and t > self.delay:
                changepoints.append(t)
        
        return changepoints


class Segmenter:
    """Window-based segmentation with BOCPD refinement."""
    
    def __init__(self, config: Dict):
        self.config = config
        model_config = config.get("model", {})
        tnc_config = model_config.get("tnc", {})
        
        self.window_size = tnc_config.get("window_size_seconds", 3.0)
        self.overlap = tnc_config.get("overlap", 0.5)
        self.sampling_rate = config.get("sampling_rates", {}).get("imu", 100)
        
        self.use_bocpd = True
        self.bocpd = BayesianOnlineChangepoint(hazard_rate=0.01)
        
    def create_windows(self, df: pd.DataFrame, 
                      channels: List[str]) -> Tuple[np.ndarray, pd.DataFrame]:
        """
        Create fixed-size windows from data.
        
        Args:
            df: Input dataframe
            channels: Channels to include in windows
            
        Returns:
            windows: Array of shape (n_windows, window_samples, n_channels)
            metadata: DataFrame with window metadata
        """
        window_samples = int(self.window_size * self.sampling_rate)
        step_samples = int(window_samples * (1 - self.overlap))
        
        # Extract channel data
        data = np.stack([df[ch].values for ch in channels], axis=1)
        
        windows = []
        metadata = []
        
        for start_idx in range(0, len(data) - window_samples + 1, step_samples):
            end_idx = start_idx + window_samples
            
            window = data[start_idx:end_idx, :]
            
            # Check for excessive missing data
            if np.isnan(window).sum() / window.size > 0.2:
                continue
            
            # Interpolate remaining NaNs
            for ch_idx in range(window.shape[1]):
                channel_data = window[:, ch_idx]
                if np.isnan(channel_data).any():
                    valid_idx = ~np.isnan(channel_data)
                    if valid_idx.sum() > 0:
                        window[:, ch_idx] = np.interp(
                            np.arange(len(channel_data)),
                            np.where(valid_idx)[0],
                            channel_data[valid_idx]
                        )
            
            windows.append(window)
            
            # Metadata
            meta = {
                "window_id": len(windows) - 1,
                "start_idx": start_idx,
                "end_idx": end_idx,
                "start_time": df["timestamp"].iloc[start_idx] if "timestamp" in df.columns else None,
                "end_time": df["timestamp"].iloc[end_idx-1] if "timestamp" in df.columns else None,
            }
            
            # Add trip/device info if available
            if "trip_id" in df.columns:
                meta["trip_id"] = df["trip_id"].iloc[start_idx]
            if "device_id" in df.columns:
                meta["device_id"] = df["device_id"].iloc[start_idx]
            
            # GPS flags
            if "lat" in df.columns and "lon" in df.columns:
                gps_valid = (~df["lat"].iloc[start_idx:end_idx].isna() & 
                           ~df["lon"].iloc[start_idx:end_idx].isna()).sum()
                meta["gps_coverage"] = gps_valid / window_samples
                
                if "accuracy" in df.columns:
                    meta["gps_accuracy_mean"] = df["accuracy"].iloc[start_idx:end_idx].mean()
            
            metadata.append(meta)
        
        windows_array = np.stack(windows, axis=0)
        metadata_df = pd.DataFrame(metadata)
        
        logger.info(f"Created {len(windows)} windows of size {window_samples} samples")
        
        return windows_array, metadata_df
    
    def refine_with_bocpd(self, df: pd.DataFrame, 
                         signal_channel: str = "accX") -> List[int]:
        """
        Use BOCPD to detect natural segment boundaries.
        
        Args:
            df: Input dataframe
            signal_channel: Channel to use for changepoint detection
            
        Returns:
            List of refined boundary indices
        """
        if signal_channel not in df.columns:
            logger.warning(f"Channel {signal_channel} not found, skipping BOCPD")
            return []
        
        data = df[signal_channel].fillna(method="ffill").fillna(method="bfill").values
        
        # Detect changepoints
        changepoints = self.bocpd.detect(data, threshold=0.5)
        
        logger.info(f"BOCPD detected {len(changepoints)} changepoints")
        
        return changepoints
    
    def segment_with_refinement(self, df: pd.DataFrame, 
                               channels: List[str]) -> Tuple[np.ndarray, pd.DataFrame]:
        """
        Segment with optional BOCPD refinement.
        
        For now, uses fixed windowing. BOCPD can be used to filter
        windows that cross maneuver boundaries.
        """
        windows, metadata = self.create_windows(df, channels)
        
        if self.use_bocpd:
            changepoints = self.refine_with_bocpd(df)
            
            # Mark windows that contain changepoints
            if changepoints:
                metadata["contains_changepoint"] = False
                
                for cp in changepoints:
                    # Find windows containing this changepoint
                    mask = ((metadata["start_idx"] <= cp) & 
                           (metadata["end_idx"] > cp))
                    metadata.loc[mask, "contains_changepoint"] = True
                
                logger.info(f"{metadata['contains_changepoint'].sum()} windows contain changepoints")
        
        return windows, metadata


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    from dataio import load_config, DataLoader
    from preprocessing import Preprocessor
    
    config = load_config("./configs/train_ssl.yml")
    dataset_config = load_config(config["dataset_config"])
    
    segmenter = Segmenter(config)
    
    loader = DataLoader("./configs/dataset.yml")
    preprocessor = Preprocessor(dataset_config)
    
    dfs = loader.load_all()
    
    if dfs:
        df = dfs[0]
        df_processed, _ = preprocessor.preprocess_pipeline(df)
        
        channels = ["accX_norm", "accY_norm", "accZ_norm", 
                   "gyroX_norm", "gyroY_norm", "gyroZ_norm"]
        
        windows, metadata = segmenter.segment_with_refinement(df_processed, channels)
        
        print(f"Windows shape: {windows.shape}")
        print(f"Metadata shape: {metadata.shape}")
        print(f"Metadata columns: {metadata.columns.tolist()}")
