from setuptools import setup
import os


def read(fname):
    """
    This is yanked from the setuptools documentation at
    http://packages.python.org/an_example_pypi_project/setuptools.html. It is
    used to read the text from the README file.
    """
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
        name='zounds',
        version='0.02',
        url='http://www.johnvinyard.com',
        author='John Vinyard',
        author_email='john.vinyard@gmail.com',
        long_description=read('README.md'),
        packages=[
            'zounds',
            'zounds.basic',
            'zounds.index',
            'zounds.learn',
            'zounds.nputil',
            'zounds.segment',
            'zounds.soundfile',
            'zounds.spectral',
            'zounds.synthesize',
            'zounds.timeseries',
            'zounds.ui'
        ],
        install_requires=['nose', 'unittest2', 'requests', 'tornado'],
        package_data={
            'nputil': ['*.pyx', '*.pyxbld'],
            'ui': ['*.html', '*.js']
        },
        include_package_data=True
)
