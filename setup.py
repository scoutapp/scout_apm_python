from glob import glob
from os.path import basename, splitext

from setuptools import find_packages, setup

setup(name='scout_apm',
      version='1.1.3',
      description='Scout Application Performance Monitoring Agent',
      long_description='Scout Application Performance Monitoring Agent',
      url='https://github.com/scoutapp/scout_apm_python',
      author='Scout',
      author_email='support@scoutapp.com',
      license='MIT',
      zip_safe=False,
      python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, <4',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
      entry_points={
          'console_scripts': [
              'core-agent-manager = scout_apm.core.cli.core_agent_manager:main'
          ]
      },
      install_requires=['psutil', 'PyYAML', 'requests'],
      keywords='apm performance monitoring development',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: System :: Monitoring',
        'License :: Other/Proprietary License',
        'Operating System :: MacOS',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
      ])
