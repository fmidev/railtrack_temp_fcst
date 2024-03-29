# Railtrack temperature forecast

Railtrack_temp_fcst generates 10 day long forecast for temperature of railtracks. 
It runs machine learning model build for this project and this code generates operative run.
Original machine learning model is trained for point-forecast and observation.
This repository creates forecast to whole Finland are. 
Original NWP-model is EC and model area is cut to describe mainly Finland.

Sourcecode of the machine learning model: https://github.com/ldaniel2016/rail_temp_ML_model.git

The usage is prioritized EC model data provided by Finnish meteorological institute FMI. 
For running the script certain input files are required:
- NWP forecast of T2m, D2m, T0m, T925hPa, WS10m, Low level clouds, Mid-level clouds, Short and Long wave radiation.
- Machine learning model to generate the forecast itself

Origin data files for testing can be downloaded only trough FMI connection with command
```wget https://routines-data.lake.fmi.fi/trail/ec/TODAY_DATA.grib2```

and ML-model 
```wget https://lake.fmi.fi/rail-temp/MODEL.grib2```

where `DATA` is name of wanted parameter and `MODEL` is name of ML-model
`TODAY` is wanted date recommend to be datetime **now** `0000` (hour_minute) after noon 
and `1200` (hour_minute) after midnight if data is downloaded from FMI database.

### railtrack_temp_fcst Installation and Usage 
For running code from a terminal, modifications for file `run_railtrack_temp.sh` is needed. 
Default setting will produce temperature forecast file. 
With modifications also data visualizations can be done. 


```
$ git clone https://github.com/fmidev/railtrack_temp_fcst.git
$ cd railtrack_temp_fcst/
$ python3 -m venv venv
$ source venv/bin/activate
(venv) $ python3 -m pip install -r requirements.txt
(venv) $ chmod +x run_railtrack_temp_fcst.sh
(venv) $ ./run_railtrack_temp_fcst.sh TODAY OUTPUT_FILE_PATH
```
Define `TODAY` as date today from current time in format `yyyymmddhhMM`.
`hhMM` needs to be `0000` after noon and `1200` after midnight.

Define `OUTPUT_FILE_PATH` as file name only with fileformat `.grib2`. For example `output_file.grib2`.
A file will be saved to current working directory.

For running script for data visualizations uncomment `lines 42 and 44` from file `run_railtrack_temp.sh`
Add comment to `line 38`. Then produce command `(venv) $ python3 run_pot_nwc.sh TODAY`