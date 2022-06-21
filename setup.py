from setuptools import find_packages, setup

from dremel3dpy.helpers.constants import (
    PROJECT_AUTHOR,
    PROJECT_CLASSIFIERS,
    PROJECT_DESCRIPTION,
    PROJECT_EMAIL,
    PROJECT_KEYWORDS,
    PROJECT_LICENSE,
    PROJECT_LONG_DESCRIPTION,
    PROJECT_NAME,
    PROJECT_URL,
    __version__,
)

DESCRIPTION = "Dremel 3D Printer API"
LONG_DESCRIPTION = "API for grabbing statistics and pausing/resuming/canceling/starting a printing job on a 3D20, 3D40 or 3D45 model."

PACKAGES = find_packages(exclude=["tests", "tests.*"])

# Setting up
setup(
    # the name must match the folder name 'verysimplemodule'
    name=PROJECT_NAME,
    version=__version__,
    description=PROJECT_DESCRIPTION,
    long_description=PROJECT_LONG_DESCRIPTION,
    author=PROJECT_AUTHOR,
    author_email=PROJECT_EMAIL,
    license=PROJECT_LICENSE,
    url=PROJECT_URL,
    platforms="any",
    py_modules=["dremel3dpy"],
    packages=PACKAGES,
    install_requires=[
        "decorator>=5.0",
        "imageio>=2.0",
        "imutils>=0.0",
        "requests>=2.0",
        "tqdm>=4.0",
        "validators>=0.0",
        "yarl>=1.0",
    ],
    keywords=PROJECT_KEYWORDS,
    classifiers=PROJECT_CLASSIFIERS,
)
