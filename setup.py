from setuptools import setup

setup(
    name="ar6_utils",
    version="0.1.0",
    author="Kaj-Ivar van der Wijst",
    author_email="k.i.vanderwijst@gmail.com",
    packages=["ar6_utils"],
    # url="http://pypi.python.org/pypi/PackageName/",
    license="LICENSE.txt",
    description="Useful for handling AR6 database files in IAMC format, and provides AR6 plot style",
    long_description=open("README.md").read(),
    install_requires=["pandas", "openpyxl"],
)
