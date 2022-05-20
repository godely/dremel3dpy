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
    keywords=PROJECT_KEYWORDS,
    classifiers=PROJECT_CLASSIFIERS,
)
