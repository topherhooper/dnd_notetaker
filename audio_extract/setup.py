"""Setup configuration for audio_extract module."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="audio_extract",
    version="0.1.0",
    author="Audio Extract Contributors",
    description="A modular audio extraction library with chunking and tracking support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/audio_extract",
    packages=['audio_extract', 'audio_extract.dashboard', 'audio_extract.drive', 'audio_extract.cli'],
    package_dir={'audio_extract': '.'},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "google-api-python-client>=2.0.0",
        "google-auth>=2.0.0",
        "google-auth-httplib2>=0.1.0",
        "google-auth-oauthlib>=0.4.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "colorlog>=6.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "audio-extract=audio_extract.dev_extract:main",
            "audio-status=audio_extract.dev_status:main",
            "audio-dashboard=audio_extract.dev_server:main",
        ],
    },
    include_package_data=True,
    package_data={
        "audio_extract": [
            "dashboard/*.html",
            "dashboard/static/*.css",
            "dashboard/static/*.js",
        ],
    },
)