"""Setup configuration for D&D Notetaker package"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="dnd-notetaker",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Automated D&D session recording processor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/dnd_notetaker",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment :: Role-Playing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "dnd-notetaker=dnd_notetaker.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "dnd_notetaker": ["*.json"],
    },
)