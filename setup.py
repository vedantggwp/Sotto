#!/usr/bin/env python3
"""
Sotto - Voice Control for macOS
Setup configuration for package installation.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

setup(
    name="sotto",
    version="0.1.0",
    author="Ved",
    author_email="",
    description="Voice control and dictation for macOS with near-zero latency",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ved/sotto",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: MacOS X",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Desktop Environment",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
    ],
    python_requires=">=3.9",
    install_requires=[
        "sounddevice>=0.4.6",
        "numpy>=1.24.0",
        "faster-whisper>=1.0.0",
        "pynput>=1.7.6",
        "rumps>=0.4.0",
        "pyobjc-core>=10.0",
        "pyobjc-framework-Cocoa>=10.0",
        "pyobjc-framework-Quartz>=10.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "pyyaml>=6.0",
        "rich>=13.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "sotto=sotto.main:main",
            "sotto-download=scripts.download_model:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
