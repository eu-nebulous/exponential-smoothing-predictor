# Copyright (c) 2023 Institute of Communication and Computer Systems
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

FROM python:3.11 as source
#RUN pip install --no-cache --upgrade pip

RUN mkdir /src
COPY ./src/ /src/

WORKDIR /src
RUN pip install --no-cache-dir -r requirements.txt && python3 setup.py sdist

FROM ubuntu:noble
RUN mkdir -p /home/r_predictions

#RUN apt-get update
ENV TZ=Europe/Athens
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install --no-install-recommends -y \
libcurl4-openssl-dev=8.5.0-2ubuntu1 \
build-essential=12.10ubuntu1 \
r-base-core=4.3.2-1build1 \
r-base-dev=4.3.2-1build1 \
r-cran-digest=0.6.34-1 \
r-cran-boot=1.3-28.1-1 \
r-cran-class=7.3-22-2 \
r-cran-cluster=2.1.6-1 \
r-cran-codetools=0.2-19-1 \
r-cran-foreign=0.8.86-1 \
r-cran-kernsmooth=2.23-22-1 \
r-cran-lattice=0.22-5-1 \
r-cran-littler=0.3.19-1 \
r-cran-mass=7.3-60-2 \
r-cran-matrix=1.6-4-1 \
r-cran-mgcv=1.9-1-1 \
r-cran-nlme=3.1.164-1 \
r-cran-nnet=7.3-19-2 \
r-cran-pkgkitten=0.2.3-1 \
r-cran-rcpp=1.0.11-1 \
r-cran-rpart=4.1.23-1 \
r-cran-spatial=7.3-17-1 \
r-cran-survival=3.5-7-1 \
r-doc-html=4.3.2-1build1 \
r-recommended=4.3.2-1build1 \
python3=3.11.4-5ubuntu1 \
python3-pip=23.3+dfsg-1  \
python3.11-venv=3.11.7-2 \
&& rm -rf /var/lib/apt/lists/*


COPY ./src/r_predictors/r_commands.R /home/r_predictions/
RUN Rscript /home/r_predictions/r_commands.R #install prerequisite libraries

COPY --from=source ./src/dist/esm_forecaster-0.1.0.tar.gz /home/r_predictions/
COPY ./src/requirements.txt /home/r_predictions/
COPY ./src/prepare_python_dependencies.sh /home/r_predictions/
RUN bash -x /home/r_predictions/prepare_python_dependencies.sh

COPY ./src/r_predictors/forecasting_real_workload.R /home/r_predictions/

#below two commented lines only serve for experiments with predictive functionality
#COPY ./default_application.csv /home/r_predictions
#RUN Rscript forecasting_real_workload.R default_application.csv MinimumCores 1638878119

WORKDIR /home/r_predictions/esm_forecaster-0.1.0

CMD ["/bin/sh","-c",". /home/forecasting_env/bin/activate && python3 -u /home/r_predictions/esm_forecaster-0.1.0/runtime/Predictor.py /home/r_predictions/esm_forecaster-0.1.0/r_predictors/prediction_configuration.properties 2>&1 > $LOG_FILE "]

