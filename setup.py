import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="muse_nanoleaf",
    version="0.0.1",
    author='Lyon Lay',
    author_email='lay.lyon@gmail.com',
    description='A muse/nanoleaf integration',
    url='https://github.com/LLay/muse_nanoleaf',
    # install_requires=['nanoleaf'],
    packages=setuptools.find_packages(),
    zip_safe=False
)
