#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="openapi-doctor",
    version="1.0.0",
    description="Production-grade OpenAPI 3.0 & 3.1 specification linter and automated autofixer",
    author="slopggobblercobbler81",
    author_email="slopggobblercobbler81@users.noreply.github.com",
    url="https://github.com/slopggobblercobbler81/openapi-doctor",
    packages=find_packages(),
    install_requires=[
        "pyyaml>=5.3",
    ],
    extras_require={
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "openapi-doctor=openapi_doctor.cli:main",
        ],
    },
    python_requires=">=3.8",
)
