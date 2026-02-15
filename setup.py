#!/usr/bin/env python3
"""Setup script for GitPulse."""

from setuptools import setup, find_packages
from pathlib import Path

long_description = Path("README.md").read_text(encoding="utf-8")

setup(
    name="gitpulse",
    version="1.0.0",
    description="Multi-Repository Health Monitor - instant health checks for all your git repos",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ATLAS (Team Brain)",
    author_email="logan@metaphy.com",
    url="https://github.com/DonkRonk17/GitPulse",
    py_modules=["gitpulse"],
    python_requires=">=3.7",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "gitpulse=gitpulse:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: Software Development :: Quality Assurance",
    ],
    keywords="git repository monitor health dashboard multi-repo",
    license="MIT",
)
