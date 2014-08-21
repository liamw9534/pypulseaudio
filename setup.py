from __future__ import unicode_literals

import re

from setuptools import setup, find_packages


def get_version(filename):
    content = open(filename).read()
    metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", content))
    return metadata['version']


setup(
    name='pypulseaudio',
    version=get_version('pypulseaudio/__init__.py'),
    url='https://github.com/liamw9534/pypulseaudio',
    license='Apache License, Version 2.0',
    author='Liam Wickins',
    author_email='liamw9534@gmail.com',
    description='Python-based PulseAudio sound management',
    long_description=open('README.rst').read(),
    packages=find_packages(exclude=['tests', 'tests.*']),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'setuptools',
        'libpulseaudio >= 1.1',
    ],
    test_suite='nose.collector',
    tests_require=[
        'nose',
        'mock >= 1.0',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries',
        'Topic :: Multimedia :: Sound/Audio',
    ],
)
