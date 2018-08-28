from glob import glob
import os
import sys

from setuptools import find_packages, setup, Extension

long_description = 'Scout Application Performance Monitoring Agent - https://scoutapp.com'
if os.path.exists('README.md'):
    long_description = open('README.md').read()

# Try to compile the extensions, except for platforms or versions
# where our extensions are not supported
compile_extensions = True

setup_args = {
      'name': 'scout_apm',
      'version': '1.3.4',
      'description': 'Scout Application Performance Monitoring Agent',
      'long_description': long_description,
      'long_description_content_type': 'text/markdown',
      'url': 'https://github.com/scoutapp/scout_apm_python',
      'author': 'Scout',
      'author_email': 'support@scoutapp.com',
      'license': 'MIT',
      'zip_safe': False,
      'python_requires': '>=3.4, <4',
      'packages': find_packages('src'),
      'package_dir': {'': 'src'},
      'py_modules': [os.splitext(os.basename(path))[0] for path in glob('src/*.py')],
      'ext_modules': [Extension('scout_apm.core.objtrace', ['src/scout_apm/core/ext/objtrace.c'])],
      'entry_points': {
          'console_scripts': [
              'core-agent-manager = scout_apm.core.cli.core_agent_manager:main'
          ]
      },
      'install_requires': ['psutil', 'PyYAML', 'requests'],
      'keywords': 'apm performance monitoring development',
      'classifiers': [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
      ]}

if sys.version_info <= (3, 0):
    compile_extensions = False

if sys.platform.startswith('java'):
    compile_extensions = False

if '__pypy__' in sys.builtin_module_names:
    compile_extensions = False

if compile_extensions is not True:
    del setup_args['ext_modules']

setup(**setup_args)
