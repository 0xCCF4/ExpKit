#!/usr/bin/env python

from distutils.core import setup
import os
from pathlib import Path

from setuptools import find_packages

lib_folder = Path(__file__).parent
requirement_path = lib_folder / 'requirements.txt'
install_requires = []

if requirement_path.exists() and requirement_path.is_file():
    install_requires = requirement_path.read_text("utf-8").splitlines()
    print("Found requirements.txt, installing dependencies...")
else:
    print(f"No requirements.txt found. Skipping installation of dependencies. {requirement_path.absolute()}")

readme_path = lib_folder / "README.md"
readme = "--- NOT FOUND ---"
if readme_path.exists() and readme_path.is_file():
    readme = readme_path.read_text("utf-8")

index = 0
while index < len(install_requires):
    install_requires[index] = install_requires[index].strip()
    if install_requires[index].startswith("#") or len(install_requires[index]) <= 0:
        install_requires.pop(index)
    else:
        index += 1

setup(name='expkit-framework',
      version='0.0.1b',
      author='0xCCF4',
      packages=find_packages(exclude=["tests", "test"]),
      install_requires=install_requires,
      url="https://0xccf4.gitlab.io/expkit/",
      description="A framework and build automation tool to process exploits/payloads to evade antivirus and endpoint detection response products using reusable building-blocks like encryption or obfuscation.",
      long_description=readme,
      long_description_content_type="text/markdown",
      python_requires=">=3.10",
      entry_points={
            'console_scripts': [
                  'expkit = expkit.framework.main:main',
            ],
        },
     )
