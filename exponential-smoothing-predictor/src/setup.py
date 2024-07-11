# Copyright (c) 2023 Institute of Communication and Computer Systems
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from distutils.core import setup

setup(
    # Application name:
    name="esm_forecaster",

    # Version number (initial):
    version="0.1.0",

    # Application author details:
    author="Andreas Tsagkaropoulos",
    author_email="atsagkaropoulos@mail.ntua.gr",

    # Packages
    packages=["r_predictors","runtime","exn","exn.core","exn.handler","exn.settings","runtime.operational_status","runtime.utilities","runtime.predictions"],

    # Include additional files into the package
    include_package_data=True,

    # Details
    #url="http://pypi.python.org/pypi/exponential_smoothing_forecaster/",

    #
    # license="LICENSE.txt",
    description="A utility to generate monitoring metric predictions for the Morphemic platform using exponential smoothing.",

    # long_description=open("README.txt").read(),

    # Dependent packages (distributions)
    install_requires=[
        "python-slugify",
        "jproperties",
        "requests",
        "numpy",
        "python-qpid-proton",
        "influxdb-client",
        "python-dotenv",
        "python-dateutil"
    ],
    #package_dir={'': '.'},
    entry_points={
        'console_scripts': [
            'start_exsmoothing = runtime.Predictor:main',
        ],
    }
)
