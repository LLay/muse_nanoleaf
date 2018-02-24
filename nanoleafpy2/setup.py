from __future__ import absolute_import
from setuptools import setup
import subprocess
from io import open

gitVersion = subprocess.check_output(u"git tag -l --points-at HEAD".split()).decode(u'UTF-8').strip()

setup(
    name=u'nanoleaf',
    packages=[u'nanoleaf'],
    version=gitVersion,
    description=u'Python interface for Nanoleaf Aurora.',
    long_description=open(u'README.rst', u'r').read(),
    author=u'Anthony Bryan',
    author_email=u'projects@anthonybryan.net',
    url=u'https://github.com/software-2/nanoleaf',
    download_url=u'https://github.com/software-2/nanoleaf/archive/' + gitVersion + u'.tar.gz',
    keywords=[u'nanoleaf', u'aurora', u'lighting', u'openAPI'],
    classifiers=[
        u'Topic :: Home Automation',
        u'License :: OSI Approved :: MIT License',
        u'Programming Language :: Python :: 3'
    ],
    install_requires=[u'requests']
)
