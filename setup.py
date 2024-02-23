from setuptools import setup


with open("README.md") as fh:
    description = fh.read()

with open("LICENSE") as fh:
    license_txt = fh.read()

setup(
    name="ar6_utils",
    version="0.1.0",
    author="Kaj-Ivar van der Wijst",
    author_email="k.i.vanderwijst@gmail.com",
    packages=["ar6_utils"],
    url="https://kvanderwijst.github.io/ar6_utils/",
    license=license_txt,
    description="Useful for handling AR6 database files in IAMC format, and provides AR6 plot style",
    long_description=description,
    install_requires=["numpy", "pandas", "plotly", "openpyxl"],
    include_package_data=True,
)
