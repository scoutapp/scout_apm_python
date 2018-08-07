from glob import glob
import os

from setuptools import find_packages, setup, Extension

long_description = 'Scout Application Performance Monitoring Agent - https://scoutapp.com'
if os.path.exists('README.md'):
    long_description = open('README.md').read()

'''
optional_exts is an array containing tuples of extenstions to compile:
    ('module_name', [files, to compile], [libraries, needed, for, compiling])

We will attempt to compile these extensions before we finalize our `setup` for
the scout_apm module. This allows us to include C extensions that can fail
to compile but the scout_apm package will work anyway (with less features)
'''
optional_exts = [('scout_apm.objtrace', ['src/scout_apm/ext/objtrace.c'], [])]


def check_extensions():
    import distutils.sysconfig
    import distutils.ccompiler
    from distutils.errors import CompileError, LinkError

    compiler = distutils.ccompiler.new_compiler()
    assert isinstance(compiler, distutils.ccompiler.CCompiler)
    distutils.sysconfig.customize_compiler(compiler)

    verified_exts = []

    for ext in optional_exts:
        try:
            compiler.link_executable(
                compiler.compile(ext[1]),
                ext[1] + '.compiled',
                libraries=ext[2],
            )
        except CompileError as e:
            print('{} compile error: {}'.format(ext[0], repr(e)))
        except LinkError as e:
            print('{} link error: {}'.format(ext[0]. repr(e)))
        else:
            verified_exts.append([
                Extension(
                    ext[0],
                    sources=ext[1],
                    libraries=ext[2],
                    ),
            ])

    return verified_exts


setup(name='scout_apm',
      version='1.3.0',
      description='Scout Application Performance Monitoring Agent',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/scoutapp/scout_apm_python',
      author='Scout',
      author_email='support@scoutapp.com',
      license='MIT',
      zip_safe=False,
      python_requires='>=3.4, <4',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      py_modules=[os.splitext(os.basename(path))[0] for path in glob('src/*.py')],
      ext_modules=check_extensions(),
      entry_points={
          'console_scripts': [
              'core-agent-manager = scout_apm.core.cli.core_agent_manager:main'
          ]
      },
      install_requires=['psutil', 'PyYAML', 'requests'],
      keywords='apm performance monitoring development',
      classifiers=[
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
      ])
