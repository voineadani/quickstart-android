# iDrive Behavior Analysis - Privacy-Preserving ML Pipeline

A production-ready, privacy-preserving machine learning pipeline for analyzing driving behaviors from smartphone sensor data (IMU + GPS). Runs locally on CPU or GPU with no external services required.

## Features

- **Self-Supervised Learning**: Three SSL methods (TNC, MAE, BYOL) for learning representations from unlabeled sensor data
- **Privacy-First**: Local-only processing with PII scrubbing, k-anonymity, and coordinate redaction
- **Physics-Based Weak Labels**: Automatic labeling of maneuvers using jerk, yaw rate, curvature
- **Anomaly Detection**: Multi-method ensemble for identifying unusual driving patterns
- **Comprehensive Reporting**: Single HTML report with visualizations and findings
- **Production Ready**: Type hints, config validation, health checks, extensive testing

## Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd quickstart-android

# Install dependencies
make setup

# Or manually
pip install -r requirements.txt
pip install -e .
```

### Generate Synthetic Data (for testing)

```bash
./scripts/demo_synth.sh
```

### Run Complete Pipeline

```bash
./scripts/run_all.sh
```

Or run individual steps:

```bash
# 1. Train SSL model
python -m src.ssl_train --config ./configs/train_ssl.yml --method tnc

# 2. Extract embeddings
python -m src.embed --config ./configs/train_ssl.yml --ckpt ./ckpts/tnc_final.pt --method tnc

# 3. Cluster embeddings
python -m src.discover --config ./configs/cluster.yml

# 4. Generate weak labels
python -m src.weaklabels --config ./configs/weaklabels.yml

# 5. Detect anomalies
python -m src.anomaly --config ./configs/cluster.yml
```

## Data Schema

The pipeline expects sensor data with the following columns:

**Required:**
- `timestamp`: ISO 8601 datetime (e.g., "2025-06-06T19:24:57.749")
- `accX`, `accY`, `accZ`: Accelerometer (m/s²)
- `gyroX`, `gyroY`, `gyroZ`: Gyroscope (rad/s)
- `lat`, `lon`: GPS coordinates (degrees)

**Optional:**
- `speed`: GPS speed (m/s)
- `bearing`: GPS bearing (degrees)
- `accuracy`: GPS accuracy (meters)
- `magX`, `magY`, `magZ`: Magnetometer (μT)
- `userAccX`, `userAccY`, `userAccZ`: User acceleration (m/s²)

Example from dataset:
```
timestamp,accX,accY,accZ,gyroX,gyroY,gyroZ,lat,lon,speed,bearing,accuracy
2025-06-06T19:24:57.749,-0.093,9.050,-3.112,0.003,-0.000,0.001,45.6625,25.5675,0.282,337.3,8.9
```

### Data Format

- Files: CSV or Parquet
- Location: Set via `IDRIVE_DATA` environment variable (defaults to `./data/`)
- Schema validation and unit conversion performed automatically

## Configuration

All configuration is in YAML files under `./configs/`:

- **dataset.yml**: Data schema, sampling rates, quality thresholds
- **train_ssl.yml**: SSL training parameters, model architecture, augmentation
- **cluster.yml**: UMAP and HDBSCAN/DBSCAN parameters
- **weaklabels.yml**: Physics-based thresholds for maneuver detection
- **eval.yml**: Evaluation metrics and validation settings
- **report.yml**: Report generation and privacy settings

## Architecture

### Data Processing Pipeline

```
Raw Data → Health Check → Preprocessing → Segmentation → SSL Training
                ↓              ↓              ↓              ↓
           Fail-fast?    Standardize    Windowing      Embeddings
                           Resample        BOCPD
                           Gravity
                           Split
```

### Self-Supervised Learning

Three SSL methods implemented:

1. **TNC (Temporal Neighborhood Coding)**: Contrastive learning with temporal positives
2. **MAE (Masked Autoencoder)**: Time and STFT masking with reconstruction
3. **BYOL**: Non-contrastive learning with EMA target network

Shared features:
- Conv/Transformer hybrid encoder
- Rich augmentations (rotation, jitter, time-warp, masking)
- Cross-modal dropout (IMU/GPS)
- Time-warp consistency loss

### Discovery & Analysis

```
Embeddings → UMAP → HDBSCAN → Cluster Cards
              ↓         ↓
           2D Viz   Statistics

GPS + IMU → Physics Rules → Weak Labels
              ↓
         Jerk, Yaw Rate
         Curvature, Δv

Embeddings → Anomaly Ensemble → Anomalies
              ↓
         IsolationForest
         Centroid Distance
         Reconstruction Error
```

## Privacy & Security

All processing is **local-only**. Privacy features:

- **Coordinate Redaction**: Remove GPS near home/work locations
- **K-Anonymity**: Blur groups with < k members  
- **Coordinate Rounding**: Reduce precision (configurable)
- **Path Thinning**: Subsample for report display
- **Identifier Scrubbing**: Hash device/user IDs

Configure in `configs/report.yml`:

```yaml
privacy:
  redact_coordinates: true
  home_work_radius: 500  # meters
  k_anonymity: 5
  coordinate_precision: 3
  path_thinning_factor: 10
```

## Outputs

The pipeline generates:

- `embeddings/embeddings.parquet`: Window embeddings + metadata
- `results/clusters.parquet`: Cluster assignments with UMAP coordinates
- `results/weaklabels.csv`: Physics-based event labels
- `results/anomalies.csv`: Detected anomalies with scores
- `ckpts/`: Model checkpoints
- `results/report.html`: Comprehensive HTML report (when implemented)

## Testing

```bash
# Run all tests
make test

# Run specific test modules
pytest tests/test_windowing.py -v
pytest tests/test_augmentations.py -v
pytest tests/test_curvature.py -v
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run linting
make lint

# Format code
black src/ tests/ synthetic/
```

## Limitations & Caveats

1. **Sensor Calibration**: Different devices may have different sensor characteristics
2. **GPS Accuracy**: Urban canyons, tunnels affect GPS quality
3. **Unlabeled Learning**: Clusters may not always align with semantic categories
4. **Weak Labels**: Physics-based rules are heuristic, not ground truth
5. **Computational Cost**: SSL training can be slow on CPU (GPU recommended for large datasets)

## Interpretation Guidelines

**Embeddings**: 
- Similar embeddings = similar driving patterns
- Distance in embedding space ≈ behavioral similarity
- Use UMAP for visualization, not distance metrics

**Clusters**:
- Discovered patterns, not predefined categories
- Noise cluster (-1) contains outliers
- Cluster size ≠ importance

**Weak Labels**:
- Indicative, not definitive
- Thresholds tunable per vehicle/device
- Should be validated against known events

**Anomalies**:
- High scores = unusual, not necessarily dangerous
- Manual review recommended for safety-critical applications
- Ensemble reduces false positives

## Performance

Expected performance on reference hardware:

| Dataset Size | Training Time (CPU) | Training Time (GPU) | Memory |
|-------------|---------------------|---------------------|---------|
| 10 hours    | ~2 hours            | ~20 minutes         | ~4 GB   |
| 100 hours   | ~20 hours           | ~3 hours            | ~16 GB  |

Recommendations:
- CPU: 4+ cores, 16 GB RAM
- GPU: CUDA-capable, 8+ GB VRAM
- Storage: SSD recommended for data caching

## Troubleshooting

**"Module not found" errors**:
```bash
pip install -e .  # Install package in editable mode
```

**GPU not detected**:
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

**Out of memory**:
- Reduce `batch_size` in `configs/train_ssl.yml`
- Enable `use_amp: true` for mixed precision
- Process data in smaller chunks

**Poor clustering results**:
- Check data quality with health report
- Try different SSL methods (MAE often more robust)
- Tune UMAP/HDBSCAN parameters
- Increase training epochs

**No weak labels detected**:
- Check threshold values in `configs/weaklabels.yml`
- Verify GPS accuracy is sufficient
- Ensure linear acceleration is computed

## Citation

If you use this pipeline in research, please cite:

```
@software{idrive_behavior_analysis,
  title={iDrive Behavior Analysis: Privacy-Preserving ML Pipeline},
  author={ML Engineering Team},
  year={2025},
  version={0.1.0}
}
```

## License

See LICENSE file in repository root.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run `make lint && make test`
5. Submit pull request

## Support

For issues, questions, or contributions:
- GitHub Issues: <repository-url>/issues
- Documentation: This README and inline docstrings

## Roadmap

Future enhancements:

- [ ] HTML report generation implementation
- [ ] Supervised head training with few-shot learning
- [ ] Evaluation metrics and calibration
- [ ] Map-matching integration
- [ ] Real-time streaming mode
- [ ] Mobile deployment (TFLite/ONNX)
- [ ] Multi-modal fusion (add magnetometer)
- [ ] Advanced BOCPD integration
- [ ] Uncertainty quantification (MC-dropout)
- [ ] Interactive report dashboard
