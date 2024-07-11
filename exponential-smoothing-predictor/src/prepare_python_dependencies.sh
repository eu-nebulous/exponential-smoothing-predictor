EXPONENTIAL_SMOOTHING_VERSION="0.1.0"
##python3 -m venv /home/forecasting_env
##. /home/forecasting_env/bin/activate
pip3 install --no-cache-dir -r /home/r_predictions/requirements.txt
cd /home/r_predictions

# Install the module itself (provided that the tar.gz file of the module has already been copied inside the container)

pip install esm_forecaster-$EXPONENTIAL_SMOOTHING_VERSION.tar.gz #--break-system-packages
##tar -xzvf esm_forecaster-$EXPONENTIAL_SMOOTHING_VERSION.tar.gz
