# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from setuptools import Extension, find_packages, setup

with open("README.md", "r") as fp:
    long_description = fp.read()

packages = find_packages("src")
if sys.version_info < (3, 6):
    packages = [p for p in packages if not p.startswith("scout_apm.async_")]

compile_extensions = (
    # Python 3+
    sys.version_info >= (3,)
    # Not Jython
    and not sys.platform.startswith("java")
    # Not PyPy
    and "__pypy__" not in sys.builtin_module_names
)
if compile_extensions:
    ext_modules = [
        Extension(
            name=str("scout_apm.core._objtrace"),
            sources=[str("src/scout_apm/core/_objtrace.c")],
            optional=True,
        )
    ]
else:
    ext_modules = []

setup(
    name="scout_apm",
    version="2.15.0",
    description="Scout Application Performance Monitoring Agent",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/scoutapp/scout_apm_python",
    project_urls={
        "Documentation": "https://docs.scoutapm.com/#python-agent",
        "Changelog": (
            "https://github.com/scoutapp/scout_apm_python/blob/master/CHANGELOG.md"
        ),
    },
    author="Scout",
    author_email="support@scoutapm.com",
    license="MIT",
    zip_safe=False,
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, <4",
    packages=packages,
    package_dir={str(""): str("src")},
    ext_modules=ext_modules,
    entry_points={
        "console_scripts": [
            "core-agent-manager = scout_apm.core.cli.core_agent_manager:main"
        ]
    },
    install_requires=[
        'asgiref ; python_version >= "3.5"',
        'importlib-metadata ; python_version < "3.8"',
        "psutil>=5,<6",
        'urllib3[secure] < 1.25 ; python_version < "3.5"',
        'urllib3[secure] < 2 ; python_version >= "3.5"',
        "wrapt>=1.10,<2.0",
    ],
    keywords="apm performance monitoring development",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Bottle",
        "Framework :: Django",
        "Framework :: Django :: 1.8",
        "Framework :: Django :: 1.9",
        "Framework :: Django :: 1.10",
        "Framework :: Django :: 1.11",
        "Framework :: Django :: 2.0",
        "Framework :: Django :: 2.1",
        "Framework :: Django :: 2.2",
        "Framework :: Django :: 3.0",
        "Framework :: Flask",
        "Framework :: Pyramid",
        "Intended Audience :: Developers",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
