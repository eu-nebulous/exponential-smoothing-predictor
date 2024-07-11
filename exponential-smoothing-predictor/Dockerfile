# Copyright (c) 2023 Institute of Communication and Computer Systems
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

FROM python:3.11 as source
#RUN pip install --no-cache --upgrade pip

RUN mkdir /src
COPY ./src/ /src/
#COPY src/requirements.txt /src/
WORKDIR /src
RUN pip install --no-cache-dir -r requirements.txt && python3 setup.py sdist

#FROM ubuntu:noble
FROM python:3.11-slim
RUN mkdir -p /home/r_predictions

#RUN apt-get update
ENV LOG_FILE=exponential_smoothing.log
ENV TZ=Europe/Athens
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install --no-install-recommends -y \
libcurl4-openssl-dev \
build-essential \
r-base-core \
r-base-dev \
r-cran-digest \
r-cran-boot \
r-cran-class \
r-cran-cluster \
r-cran-codetools \
r-cran-foreign \
r-cran-kernsmooth \
r-cran-lattice \
r-cran-littler \
r-cran-mass \
r-cran-matrix \
r-cran-mgcv \
r-cran-nlme \
r-cran-nnet \
r-cran-pkgkitten \
r-cran-rcpp \
r-cran-rpart \
r-cran-spatial \
r-cran-survival \
r-doc-html \
r-recommended \
&& rm -rf /var/lib/apt/lists/*


COPY --from=source /src/r_predictors/r_commands.R /home/r_predictions/
RUN Rscript /home/r_predictions/r_commands.R #install prerequisite libraries

COPY --from=source /src/dist/esm_forecaster-0.1.0.tar.gz /home/r_predictions/
COPY --from=source /src/requirements.txt /home/r_predictions/
COPY --from=source /src/prepare_python_dependencies.sh /home/r_predictions/
RUN bash -x /home/r_predictions/prepare_python_dependencies.sh

COPY --from=source /src/r_predictors/forecasting_real_workload.R /home/r_predictions/
COPY --from=source /src/r_predictors/prediction_configuration.properties /home/r_predictions/

#The two commented lines below only serve for experiments with predictive functionality

#COPY ./default_application.csv /home/r_predictions
#RUN Rscript forecasting_real_workload.R default_application.csv MinimumCores 1638878119

#WORKDIR /home/r_predictions/esm_forecaster-0.1.0

CMD ["/usr/local/bin/start_exsmoothing","/home/r_predictions/prediction_configuration.properties"," > $LOG_FILE 2>&1 "]

