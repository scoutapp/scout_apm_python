# coding=utf-8

import os
import sys

from setuptools import Extension, find_packages, setup

with open("README.md", "r") as fp:
    long_description = fp.read()

packages = find_packages("src")

compile_extensions = (
    # Python 3+
    sys.version_info >= (3,)
    # Not Jython
    and not sys.platform.startswith("java")
    # Not PyPy
    and "__pypy__" not in sys.builtin_module_names
    # Not explicitly disabled
    and (os.environ.get("SCOUT_DISABLE_EXTENSIONS", "") == "")
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
    version="3.3.0",
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
    python_requires=">=3.8, <4",
    packages=packages,
    package_dir={str(""): str("src")},
    ext_modules=ext_modules,
    entry_points={
        "console_scripts": [
            "core-agent-manager = scout_apm.core.cli.core_agent_manager:main"
        ]
    },
    install_requires=[
        "asgiref",
        "psutil>=5",
        "urllib3~=2.2.0",
        "certifi",
        "wrapt>=1.10,<2.0",
    ],
    keywords=["apm", "performance monitoring", "development"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Bottle",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 4.1",
        "Framework :: Django :: 4.2",
        "Framework :: Flask",
        "Intended Audience :: Developers",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
