from setuptools import setup, find_packages

setup(
    name="idrive-behavior-analysis",
    version="0.1.0",
    description="Privacy-preserving ML pipeline for driving behavior analysis",
    author="ML Engineering Team",
    packages=find_packages(exclude=["tests", "notebooks", "scripts"]),
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.21.0",
        "pandas>=1.3.0",
        "scipy>=1.7.0",
        "scikit-learn>=1.0.0",
        "pyarrow>=6.0.0",
        "torch>=1.10.0",
        "umap-learn>=0.5.0",
        "hdbscan>=0.8.27",
        "matplotlib>=3.4.0",
        "seaborn>=0.11.0",
        "plotly>=5.0.0",
        "pyyaml>=5.4.0",
        "pydantic>=1.8.0",
        "pyproj>=3.2.0",
        "tqdm>=4.62.0",
        "joblib>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.2.0",
            "pytest-cov>=2.12.0",
            "black>=21.0",
            "flake8>=3.9.0",
            "mypy>=0.910",
            "pre-commit>=2.15.0",
        ]
    },
)
