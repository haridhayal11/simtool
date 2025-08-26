#!/usr/bin/env python3

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="simtool",
    version="0.1.0",
    author="Haridhayal Maheswaran",
    author_email="haridhayal@gmail.com",
    description="A CLI tool to bridge ModelSim workflows to open-source simulation tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/haridhayal11/simtool",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=6.0",
        "colorama>=0.4.0",
        "cocotb>=1.7.0",
    ],
    entry_points={
        "console_scripts": [
            "simtool=simtool.cli:main",
        ],
    },
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
        ]
    }
)