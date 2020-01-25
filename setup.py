from setuptools import setup
# from setuptools.command.install import install # only needed if we want to subclass 'install'
# apparently this will look in ./pipe1/__init__.py by default
# from pipe1 import __version__

setup(
    name = "pipe1",
    version = "0.0.2",
    description = "Utilities for downloading OSM tiles",
    license = "GPL-3",
    author = "AgileBeat",
    author_email = "scott.marchese@agilebeat.com",
    url = "https://github.com/agilebeat-inc/pipeline-1",
    packages = ['pipe1'],
    scripts = ['bin/download_tiles'],
    python_requires = '>=3.6',
    install_requires = [
        'numpy >= 1.17','pandas >= 0.25','shapely >= 1.6',
        'osmxtract >= 0.0.1','pillow >= 6.2','matplotlib ~= 3.1.2',
        'wheel ~= 0.33'
    ]
)