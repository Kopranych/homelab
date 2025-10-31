#!/usr/bin/env python3
"""Setup script for photo consolidation tool."""

from setuptools import setup, find_packages
from pathlib import Path

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
with open(requirements_path) as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Use a static version to avoid import issues during build
__version__ = "1.0.0"

setup(
    name="photo-consolidator",
    version=__version__,
    description="Safe photo consolidation tool with copy-first approach",
    author="Homelab Team", 
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'consolidate=consolidate:cli',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)