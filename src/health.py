"""
Sensor health monitoring: missingness, clipping, bias drift, PSDs.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from scipy import signal, stats
import logging

logger = logging.getLogger(__name__)


class SensorHealthChecker:
    """Monitor sensor data quality and health."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.quality_thresholds = config.get("quality", {})
        
    def check_missingness(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate missing data percentage per column."""
        missing = {}
        for col in df.columns:
            if col == "timestamp":
                continue
            missing_pct = df[col].isna().sum() / len(df) * 100
            missing[col] = missing_pct
            
            if missing_pct > 10:
                logger.warning(f"{col} has {missing_pct:.1f}% missing data")
        
        return missing
    
    def check_clipping(self, df: pd.DataFrame, channels: List[str]) -> Dict[str, Dict]:
        """Detect clipping/saturation in sensor channels."""
        clipping = {}
        
        for channel in channels:
            if channel not in df.columns:
                continue
                
            data = df[channel].dropna()
            if len(data) == 0:
                continue
            
            # Check for repeated max/min values
            value_counts = data.value_counts()
            most_common_val = value_counts.index[0]
            most_common_pct = value_counts.iloc[0] / len(data) * 100
            
            # Statistical outlier detection
            q99 = data.quantile(0.99)
            q01 = data.quantile(0.01)
            clipped_high = (data >= q99).sum() / len(data) * 100
            clipped_low = (data <= q01).sum() / len(data) * 100
            
            clipping[channel] = {
                "most_common_value": float(most_common_val),
                "most_common_pct": float(most_common_pct),
                "clipped_high_pct": float(clipped_high),
                "clipped_low_pct": float(clipped_low),
            }
            
            if most_common_pct > 5:
                logger.warning(f"{channel} has {most_common_pct:.1f}% at value {most_common_val}")
        
        return clipping
    
    def check_bias_drift(self, df: pd.DataFrame, channels: List[str], 
                        window_size: int = 1000) -> Dict[str, Dict]:
        """Detect bias drift over time."""
        drift = {}
        
        for channel in channels:
            if channel not in df.columns:
                continue
                
            data = df[channel].dropna().values
            if len(data) < window_size * 2:
                continue
            
            # Calculate rolling mean
            rolling_mean = pd.Series(data).rolling(window_size, center=True).mean()
            
            # Measure drift as change in mean
            start_mean = rolling_mean.iloc[:window_size].mean()
            end_mean = rolling_mean.iloc[-window_size:].mean()
            drift_amount = abs(end_mean - start_mean)
            
            # Trend detection
            x = np.arange(len(rolling_mean))
            valid_idx = ~np.isnan(rolling_mean)
            if valid_idx.sum() > 10:
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    x[valid_idx], rolling_mean[valid_idx]
                )
                
                drift[channel] = {
                    "drift_amount": float(drift_amount),
                    "slope": float(slope),
                    "r_squared": float(r_value**2),
                    "p_value": float(p_value),
                }
                
                if p_value < 0.05 and abs(r_value) > 0.5:
                    logger.warning(f"{channel} shows significant drift (p={p_value:.3f})")
        
        return drift
    
    def compute_psd(self, df: pd.DataFrame, channels: List[str], 
                   sampling_rate: float) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        """Compute Power Spectral Density."""
        psds = {}
        
        for channel in channels:
            if channel not in df.columns:
                continue
                
            data = df[channel].dropna().values
            if len(data) < 256:
                continue
            
            # Compute PSD using Welch's method
            freqs, psd = signal.welch(data, fs=sampling_rate, nperseg=min(256, len(data)//4))
            
            psds[channel] = (freqs, psd)
        
        return psds
    
    def check_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """Identify temporal gaps in data."""
        if "timestamp" not in df.columns:
            return []
        
        timestamps = pd.to_datetime(df["timestamp"])
        time_diffs = timestamps.diff().dt.total_seconds()
        
        max_gap = self.quality_thresholds.get("max_gap_seconds", 5.0)
        gaps = time_diffs[time_diffs > max_gap]
        
        gap_info = []
        for idx, gap in gaps.items():
            gap_info.append({
                "index": int(idx),
                "gap_seconds": float(gap),
                "timestamp": str(timestamps.iloc[idx])
            })
        
        if gaps.any():
            logger.warning(f"Found {len(gaps)} gaps > {max_gap}s")
        
        return gap_info
    
    def generate_report(self, df: pd.DataFrame, imu_channels: List[str], 
                       gps_channels: List[str], sampling_rate: float) -> Dict:
        """Generate comprehensive health report."""
        report = {
            "n_samples": len(df),
            "duration_seconds": None,
            "missingness": self.check_missingness(df),
            "clipping": self.check_clipping(df, imu_channels),
            "drift": self.check_bias_drift(df, imu_channels),
            "gaps": self.check_gaps(df),
            "psds": self.compute_psd(df, imu_channels, sampling_rate),
        }
        
        # Calculate duration
        if "timestamp" in df.columns:
            timestamps = pd.to_datetime(df["timestamp"])
            duration = (timestamps.max() - timestamps.min()).total_seconds()
            report["duration_seconds"] = duration
        
        # Check critical failures
        critical_channels = [ch for ch, spec in self.config.get("schema", {}).items() 
                           if spec.get("required", False)]
        
        missing_critical = [ch for ch in critical_channels 
                          if ch not in df.columns or df[ch].isna().all()]
        
        if missing_critical:
            report["critical_failures"] = missing_critical
            logger.error(f"Critical channels missing: {missing_critical}")
        else:
            report["critical_failures"] = []
        
        return report
    
    def should_fail_fast(self, report: Dict) -> bool:
        """Determine if data quality is too poor to proceed."""
        # Check critical failures
        if report.get("critical_failures"):
            return True
        
        # Check excessive missingness
        missingness = report.get("missingness", {})
        if any(pct > 50 for pct in missingness.values()):
            logger.error("Excessive missingness detected")
            return True
        
        # Check for extremely short duration
        min_duration = self.quality_thresholds.get("min_trip_duration_seconds", 60.0)
        if report.get("duration_seconds", 0) < min_duration:
            logger.error(f"Duration {report['duration_seconds']}s < minimum {min_duration}s")
            return True
        
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    from dataio import load_config, DataLoader
    
    config = load_config("./configs/dataset.yml")
    checker = SensorHealthChecker(config)
    
    loader = DataLoader("./configs/dataset.yml")
    dfs = loader.load_all()
    
    if dfs:
        df = dfs[0]
        imu_channels = ["accX", "accY", "accZ", "gyroX", "gyroY", "gyroZ"]
        gps_channels = ["lat", "lon", "speed"]
        
        report = checker.generate_report(df, imu_channels, gps_channels, 
                                        sampling_rate=100.0)
        
        print(f"Health report:")
        print(f"  Samples: {report['n_samples']}")
        print(f"  Duration: {report['duration_seconds']:.1f}s")
        print(f"  Critical failures: {report['critical_failures']}")
        
        if checker.should_fail_fast(report):
            print("FAIL: Data quality too poor")
        else:
            print("PASS: Data quality acceptable")
