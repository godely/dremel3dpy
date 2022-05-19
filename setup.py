from setuptools import find_packages, setup

VERSION = "0.0.1"
DESCRIPTION = "Dremel 3D Printer API"
LONG_DESCRIPTION = "API for grabbing statistics and pausing/resuming/canceling/starting a printing job on a 3D20, 3D40 or 3D45 model."

# Setting up
setup(
    # the name must match the folder name 'verysimplemodule'
    name="dremel3dpy",
    version=VERSION,
    author="Gustavo Stor",
    author_email="gus@storhub.io",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    install_requires=[
        "async-timeout==4.0.2",
        "certifi==2022.5.18",
        "charset-normalizer==2.0.12",
        "decorator==5.1.1",
        "idna==3.3",
        "multidict==6.0.2",
        "requests==2.27.1",
        "six==1.16.0",
        "urllib3==1.26.9",
        "validators==0.19.0",
        "yarl==1.7.2",
    ],
    keywords=["python", "dremel", "3d", "printer", "3d-printer"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ],
)
