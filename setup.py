#!/usr/bin/env python

"""
setup.py
"""

from setuptools import setup, find_packages

setup(
    name='CMservice',
    version='1.0.0',
    description='',
    author='DIRG',
    author_email='dirg@its.umu.se',
    license='Apache 2.0',
    url='',
    packages=find_packages('src/'),
    package_dir={'': 'src'},
    package_data={
        'cmservice.service': [
            'data/i18n/locales/*/LC_MESSAGES/*.po',
            'templates/*.mako',
            'site/static/*',
        ],
    },
    classifiers=['Development Status :: 4 - Beta',
                 'Topic :: Software Development :: Libraries :: Python Modules',
                 'Programming Language :: Python :: 3.4'],
    install_requires=[
        'Flask',
        'pyjwkest',
        'Flask-Babel',
        'Flask-Mako',
        'dataset'],
    zip_safe=False,
    message_extractors={'.': [
        ('src/cmservice/**.py', 'python', None),
        ('src/cmservice/**/service/templates/**.mako', 'mako', None),
        ('src/cmservice/**/service/site/**', 'ignore', None)
    ]}
)
