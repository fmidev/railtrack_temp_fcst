#!/bin/bash
# Run script for the railtrack temperature forecast

PYTHON=python3
START_TIME=$1
OUTPUT=$2

# Load data from S3
T2=s3://trail/ec/"$START_TIME"_T-K_2.grib2
D2=s3://trail/ec/"$START_TIME"_TD-K_2.grib2
SKT=s3://trail/ec/"$START_TIME"_T-K_0.grib2
T_925=s3://trail/ec/"$START_TIME"_T-K_925.grib2
WS=s3://trail/ec/"$START_TIME"_FF-MS_10.grib2
LCC=s3://trail/ec/"$START_TIME"_NL-PRCNT_0.grib2
MCC=s3://trail/ec/"$START_TIME"_NM-PRCNT_0.grib2
SRR=s3://trail/ec/"$START_TIME"_RNETSWA-JM2_0.grib2
STR=s3://trail/ec/"$START_TIME"_RNETLWA-JM2_0.grib2
ML=xgb_random_model_no_latlon_TRail.joblib

#Local file run
# Create needed directories and download data to your "test_data" directory. You can modify file path if needed
#T2="$PWD"/test_data/"$START_TIME"_T-K_2.grib2
#D2="$PWD"/test_data/"$START_TIME"_TD-K_2.grib2
#SKT="$PWD"/test_data/"$START_TIME"_T-K_0.grib2
#T_925="$PWD"/test_data/"$START_TIME"_T-K_925.grib2
#WS="$PWD"/test_data/"$START_TIME"_FF-MS_10.grib2
#LCC="$PWD"/test_data/"$START_TIME"_NL-PRCNT_0.grib2
#MCC="$PWD"/test_data/"$START_TIME"_NM-PRCNT_0.grib2
#SRR="$PWD"/test_data/"$START_TIME"_RNETSWA-JM2_0.grib2
#STR="$PWD"/test_data/"$START_TIME"_RNETLWA-JM2_0.grib2
#ML=s3://rail-temp/xgb_random_model_no_latlon_TRail.joblib

#Generating 10-day forecast for railtrack temperature
$PYTHON ./generate_ML_temperature_rail_fcst.py --T2 "$T2" --D2 "$D2" --SKT "$SKT" --T_925 "$T_925" --WS "$WS" --LCC "$LCC" --MCC "$MCC" --SRR1h "$SRR" --STR1h "$STR" --ML_model "$ML" --output_file "$OUTPUT"

# Uncomment Python run call for doing visualizations
# Check if "figures" is in project. If not, create one
#mkdir -p "$PWD"/figures
# Generating visualizations for each forecasted time steps
#$PYTHON plotting.py --input_file $OUTPUT