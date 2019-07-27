# coding=utf-8
import os
import sys
from glob import glob

from setuptools import Extension, find_packages, setup

long_description = (
    "Scout Application Performance Monitoring Agent - https://scoutapm.com"
)
if os.path.exists("README.md"):
    with open("README.md", "r") as fp:
        long_description = fp.read()

# Try to compile the extensions, except for platforms or versions
# where our extensions are not supported
compile_extensions = True

setup_args = {
    "name": "scout_apm",
    "version": "2.2.0",
    "description": "Scout Application Performance Monitoring Agent",
    "long_description": long_description,
    "long_description_content_type": "text/markdown",
    "url": "https://github.com/scoutapp/scout_apm_python",
    "author": "Scout",
    "author_email": "support@scoutapm.com",
    "license": "MIT",
    "zip_safe": False,
    "python_requires": ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, <4",
    "packages": find_packages("src"),
    "package_dir": {"": "src"},
    "py_modules": [os.splitext(os.basename(path))[0] for path in glob("src/*.py")],
    "ext_modules": [
        Extension("scout_apm.core.objtrace", ["src/scout_apm/core/ext/objtrace.c"])
    ],
    "entry_points": {
        "console_scripts": [
            "core-agent-manager = scout_apm.core.cli.core_agent_manager:main"
        ]
    },
    "install_requires": ["psutil", "requests"],
    "keywords": "apm performance monitoring development",
    "classifiers": [
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
    ],
}

if sys.version_info <= (3, 0):
    compile_extensions = False

if sys.platform.startswith("java"):
    compile_extensions = False

if "__pypy__" in sys.builtin_module_names:
    compile_extensions = False

if not compile_extensions:
    del setup_args["ext_modules"]

setup(**setup_args)
