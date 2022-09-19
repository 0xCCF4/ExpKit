#!/usr/bin/env python

from distutils.core import setup
import os

lib_folder = os.path.dirname(os.path.realpath(__file__))
requirement_path = lib_folder + '/requirements.txt'
install_requires = []

if os.path.isfile(requirement_path):
    with open(requirement_path, "r") as f:
        install_requires = f.read().splitlines()

index = 0
while index < len(install_requires):
    install_requires[index] = install_requires[index].strip()
    if install_requires[index].startswith("#") or len(install_requires[index]) <= 0:
        install_requires.pop(index)
    else:
        index += 1

setup(name='expkit',
      version='1.0',
      description='TWINSEC Exploit Framework',
      author='Johannes Lenzen',
      author_email='johannes.lenzen@twinsec.de',
      packages=['expkit'],
      install_requires=install_requires,
      entry_points={
            'console_scripts': [
                  'expkit = expkit.framework.main:main',
            ],
        },
     )
