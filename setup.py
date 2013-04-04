from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='hcpdlstat',
      version='0.1',
      description='Tools for HCP XNAT/Aspera download analytics',
      long_description=readme(),
      url='http://github.com/karchie/hcpdlstat',
      author='Kevin A. Archie',
      author_email='karchie@wustl.edu',
      license='BSD',
      classifiers = [
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.7',
        'Topic :: Utilities',
        ],
      packages=['hcpdlstat'],
      entry_points = {
          'console_scripts':['geolocate=hcpdlstat.geolocate:main',
                             'update_dl_stats=hcpdlstat.update:main']
        },
      install_requires=[
        'openpyxl',
        'PyMySQL',
        'pyparsing==1.5.7',
        ],
      zip_safe=False)
