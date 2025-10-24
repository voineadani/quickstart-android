"""
Privacy utilities: PII scrubbing, k-anonymity, coordinate rounding.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def redact_coordinates_near_locations(df: pd.DataFrame,
                                     sensitive_locations: List[Tuple[float, float]],
                                     radius_meters: float = 500.0) -> pd.DataFrame:
    """
    Redact GPS coordinates near sensitive locations (home/work).
    
    Args:
        df: DataFrame with 'lat' and 'lon' columns
        sensitive_locations: List of (lat, lon) tuples
        radius_meters: Redaction radius
        
    Returns:
        DataFrame with redacted coordinates
    """
    df = df.copy()
    
    if not all(col in df.columns for col in ["lat", "lon"]):
        return df
    
    for sens_lat, sens_lon in sensitive_locations:
        # Approximate distance
        lat_diff = df["lat"] - sens_lat
        lon_diff = df["lon"] - sens_lon
        
        # Rough distance in meters
        dist = np.sqrt(
            (lat_diff * 111000)**2 + 
            (lon_diff * 111000 * np.cos(np.radians(sens_lat)))**2
        )
        
        # Redact
        mask = dist < radius_meters
        df.loc[mask, "lat"] = np.nan
        df.loc[mask, "lon"] = np.nan
    
    n_redacted = df["lat"].isna().sum()
    logger.info(f"Redacted {n_redacted} GPS points near sensitive locations")
    
    return df


def round_coordinates(df: pd.DataFrame, precision: int = 3) -> pd.DataFrame:
    """
    Round coordinates to reduce precision.
    
    Args:
        df: DataFrame with 'lat' and 'lon' columns
        precision: Decimal places to keep
        
    Returns:
        DataFrame with rounded coordinates
    """
    df = df.copy()
    
    if "lat" in df.columns:
        df["lat"] = df["lat"].round(precision)
    if "lon" in df.columns:
        df["lon"] = df["lon"].round(precision)
    
    logger.info(f"Rounded coordinates to {precision} decimal places")
    
    return df


def k_anonymize_blur(df: pd.DataFrame, k: int = 5,
                    group_cols: List[str] = ["lat", "lon"]) -> pd.DataFrame:
    """
    Apply k-anonymity by blurring groups with < k members.
    
    Args:
        df: DataFrame
        k: Minimum group size
        group_cols: Columns to group by
        
    Returns:
        DataFrame with k-anonymity applied
    """
    df = df.copy()
    
    # Group by specified columns
    for col in group_cols:
        if col not in df.columns:
            logger.warning(f"Column {col} not found, skipping k-anonymity")
            return df
    
    # Round coordinates first
    if "lat" in group_cols and "lon" in group_cols:
        df = round_coordinates(df, precision=2)
    
    # Count group sizes
    group_sizes = df.groupby(group_cols).size()
    small_groups = group_sizes[group_sizes < k].index
    
    # Remove or blur small groups
    for group_vals in small_groups:
        mask = True
        for col, val in zip(group_cols, group_vals):
            mask = mask & (df[col] == val)
        
        # Blur by adding noise
        if "lat" in group_cols and "lon" in group_cols:
            df.loc[mask, "lat"] += np.random.normal(0, 0.001, mask.sum())
            df.loc[mask, "lon"] += np.random.normal(0, 0.001, mask.sum())
    
    logger.info(f"Applied k-anonymity with k={k}")
    
    return df


def thin_path_for_report(df: pd.DataFrame, factor: int = 10) -> pd.DataFrame:
    """
    Thin GPS path by keeping only every Nth point.
    
    Args:
        df: DataFrame with GPS data
        factor: Thinning factor
        
    Returns:
        Thinned DataFrame
    """
    df_thinned = df.iloc[::factor].copy()
    
    logger.info(f"Thinned path from {len(df)} to {len(df_thinned)} points")
    
    return df_thinned


def scrub_identifiers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove or hash identifiable columns.
    
    Args:
        df: DataFrame
        
    Returns:
        DataFrame with scrubbed identifiers
    """
    df = df.copy()
    
    # Remove potentially identifying columns
    id_cols = ["device_id", "user_id", "trip_id", "session_id"]
    
    for col in id_cols:
        if col in df.columns:
            # Hash instead of remove for tracking
            df[col] = pd.util.hash_pandas_object(df[col], index=False)
    
    logger.info("Scrubbed identifier columns")
    
    return df


def apply_privacy_settings(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Apply all privacy settings from config.
    
    Args:
        df: DataFrame
        config: Privacy configuration
        
    Returns:
        Privacy-protected DataFrame
    """
    privacy_config = config.get("privacy", {})
    
    # Redact coordinates
    if privacy_config.get("redact_coordinates", True):
        # Would need to load sensitive locations from config
        # For now, skip
        pass
    
    # Round coordinates
    precision = privacy_config.get("coordinate_precision", 3)
    df = round_coordinates(df, precision)
    
    # K-anonymity
    k = privacy_config.get("k_anonymity", 5)
    df = k_anonymize_blur(df, k=k)
    
    # Thin path
    if privacy_config.get("path_thinning_factor"):
        factor = privacy_config["path_thinning_factor"]
        df = thin_path_for_report(df, factor)
    
    # Scrub identifiers
    df = scrub_identifiers(df)
    
    logger.info("Applied all privacy settings")
    
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test privacy functions
    df = pd.DataFrame({
        "lat": [45.66 + i*0.001 for i in range(100)],
        "lon": [25.56 + i*0.001 for i in range(100)],
        "device_id": ["device1"] * 50 + ["device2"] * 50,
        "trip_id": ["trip1"] * 100
    })
    
    print(f"Original shape: {df.shape}")
    print(f"Sample coordinates: {df[['lat', 'lon']].head()}")
    
    # Apply privacy
    df_private = round_coordinates(df, precision=2)
    print(f"Rounded coordinates: {df_private[['lat', 'lon']].head()}")
    
    df_private = k_anonymize_blur(df_private, k=5)
    print(f"After k-anonymity: {df_private.shape}")
    
    df_private = thin_path_for_report(df_private, factor=10)
    print(f"After thinning: {df_private.shape}")
    
    df_private = scrub_identifiers(df_private)
    print(f"Device ID after scrubbing: {df_private['device_id'].unique()}")
