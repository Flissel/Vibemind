#!/usr/bin/env python3
"""
Setup script for Sakana Desktop Assistant
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="sakana-desktop-assistant",
    version="0.1.0",
    author="Nicolas K. Perkins",
    author_email="nicolas.kperkins@gmail.com",
    description="Self-learning desktop AI assistant inspired by Sakana AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nickinper/sakana-desktop-assistant",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "aiofiles>=24.1.0",
        "asyncio>=3.4.3",
        "python-dotenv>=1.0.0",
        "sqlalchemy>=2.0.31",
        "aiosqlite>=0.20.0",
        "numpy>=1.26.4",
        "scikit-learn>=1.5.1",
        "requests>=2.32.3",
        "pyyaml>=6.0.1",
        "loguru>=0.7.2",
        "psutil>=5.9.0",
    ],
    extras_require={
        "llm": [
            "openai>=1.35.0",
            "llama-cpp-python>=0.2.90",
            "transformers>=4.44.0",
            "torch>=2.4.0",
        ],
        "voice": [
            "speechrecognition>=3.10.4",
            "pyttsx3>=2.90",
        ],
        "dev": [
            "pytest>=8.2.2",
            "pytest-asyncio>=0.23.7",
            "pytest-cov>=5.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "sakana=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)