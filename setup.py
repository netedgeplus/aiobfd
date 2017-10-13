#!/usr/bin/env python3

"""aiobfd setup"""

from distutils.core import setup
from setuptools import find_packages

setup(name='aiobfd',
      version='0.2',
      description='Asynchronous BFD Daemon',
      author='Kris Lambrechts',
      author_email='kris@netedge.plus',
      license='MIT',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Framework :: AsyncIO',
          'Intended Audience :: Telecommunications Industry',
          'Topic :: System :: Networking :: Monitoring :: Hardware Watchdog',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3 :: Only',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
      ],
      keywords='BFD Bidirectional Forwarding Detection rfc5880',
      url='https://github.com/netedgeplus/aiobfd',
      packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
      install_requires=['bitstring'],
      tests_require=['pytest', 'pytest-asyncio', 'pytest-cov', 'pytest-mock',
                     'coverage'],
      python_requires='>=3.5, <4',
      entry_points={'console_scripts': ['aiobfd=aiobfd.__main__:main']})
