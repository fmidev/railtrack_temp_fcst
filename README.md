# Railtrack temperature forecast

Thundercast is a Python package for generating short-period nowcast for probability of thunder. 
The system takes input information from nowcast model and observations of thunder strikes. 
Data sources are optimized mainly for Finnish meteorological institute and downloading data from FMI databases also
requires rights for a user. 
The package is also build for high grid resolution of ~1km and 15min timestep data 
so data rawer than that might not work or might produce wierd output fields.

The usage is prioritized model and observation data provided by Finnish meteorological institute FMI. 
For running the script certain input files are required:
- Instant precipitation fields of **wanted date**, and three previous time steps (Four files in total)
- Model file with param `Probability of thunder(storms)` as a base data field and a source metadata from previous timestep

Origin data files for testing can be downloaded only trough FMI connection with command
```wget https://routines-data.lake.fmi.fi/hrnwc/preop/TODAY/DATA.grib2```

where `DATA` for **Instant precipitation** is `interpolated_rprate` and for 
**Probability of thunderstorms** is `mnwc_tstm`. 

`TODAY` is wanted date recommend to be datetime **now** in 15min accuracy or datetime within 24h if data is downloaded from FMI database.

### Thundercast Installation and Usage 
For running code from a terminal modifications for file `run_pot_nwc.sh` is needed. 
Default setting will produce POT nowcast file. 
With modifications also data visualizations can be done. 


```
$ git clone https://github.com/fmidev/thundercast
$ cd thundercast/
$ python3 -m venv venv
$ source venv/bin/activate
(venv) $ python3 -m pip install .
(venv) $ python3 run_pot_nwc.sh TODAY
```
Define `TODAY` as date today or date from last 24 hours from current time in format `yyyymmddhhMM`.

For running script for data visualizations uncomment line 91 from file `run_pot_nwc.sh`
and add comment to line 88. Then produce command `(venv) $ python3 run_pot_nwc.sh TODAY`