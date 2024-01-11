import numpy as np
import xarray as xr
import warnings
import pandas as pd
import fsspec
import joblib
from datetime import datetime as dt
warnings.simplefilter(action='ignore', category=FutureWarning)


def read_file_from_s3(data_file):
    uri = "simplecache::{}".format(data_file)
    try:
        return fsspec.open_local(
            uri, s3={'anon': True,
                     'client_kwargs': {'endpoint_url': 'https://routines-data.lake.fmi.fi'}})
    except FileNotFoundError as e:
        return fsspec.open_local(
            uri, s3={'anon': True,
                     'client_kwargs': {'endpoint_url': 'https://lake.fmi.fi'}})


def load_ML_model(path: str):
    model_file = path
    if path.startswith("s3://"):
        model_file = read_file_from_s3(path)
    regressor = joblib.load(model_file)
    return regressor


def fetch_basic_predictor_files(args) -> dict:
    return {'T2': args.T2,
            'D2': args.D2,
            'SKT': args.SKT,
            'T_925': args.T_925,
            'WS': args.WS,
            'LCC': args.LCC,
            'MCC': args.MCC,
            'SRR1h': args.SRR1h,
            'STR1h': args.STR1h}


def generate_ML_forecast_domain(ds, model, data):
    rail_temp_fcst = np.zeros(shape=data.shape)
    for i in range(len(ds['time'].values)):
        df = select_domain_data_from_ds(ds, i)
        temp_fcst = model.predict(df)
        rail_temp_fcst[i] = (temp_fcst.reshape(rail_temp_fcst[0].shape))
    return rail_temp_fcst


def select_domain_data_from_ds(ds, i):
    columns_to_select = ['forecast_period', 'T2', 'D2', 'SKT', 'T_925', 'WS', 'LCC', 'MCC',
                         'sinhour', 'coshour', 'sinmonth', 'cosmonth', 'SRR1h', 'STR1h', 'month']
    data = {col: ds[col].values[i].flatten() for col in columns_to_select}
    df = pd.DataFrame(data)
    return df


def generate_ML_forecast_points(ds, model):
    len_x = len(ds.T2.values[0, :, 0])
    len_y = len(ds.T2.values[0, 0, :])
    rail_temp_fcst = np.array([[model.predict(select_df_data_from_ds(ds, i, j)) for j in range(len_y)] for i in range(len_x)])
    rail_temp_fcst = np.transpose(rail_temp_fcst, (2, 0, 1)) - 273.15
    return rail_temp_fcst


def select_df_data_from_ds(ds, i, j):
    data = {'lat': ds['lat'].values[:, i, j],
            'lon': ds['lon'].values[:, i, j],
            'forecast_period': ds['forecast_period'].values[:, i, j],
            'T2': ds['T2'].values[:, i, j],
            'D2': ds['D2'].values[:, i, j],
            'SKT': ds['SKT'].values[:, i, j],
            'T_925': ds['T_925'].values[:, i, j],
            'WS': ds['WS'].values[:, i, j],
            'LCC': ds['LCC'].values[:, i, j],
            'MCC': ds['MCC'].values[:, i, j],
            'sinhour': ds['sinhour'].values[:, i, j],
            'coshour': ds['coshour'].values[:, i, j],
            'sinmonth': ds['sinmonth'].values[:, i, j],
            'cosmonth': ds['cosmonth'].values[:, i, j],
            'SRR1h': ds['SRR1h'].values[:, i, j],
            'STR1h': ds['STR1h'].values[:, i, j],
            'month': ds['month'].values[:, i, j]}
    df = pd.DataFrame(data)
    return df.values


def add_data_to_dataset_2d(param_name, ds, i) -> xr.Dataset:
    ds[param_name] = (["x", "y"], ds[param_name][i, :, :])
    return ds


def expand_array_with_time_dimension(time, data):
    new_lat = np.zeros(shape=(len(time), len(data[0][0:]), len(data[0][0])))
    new_lon = np.zeros(shape=(len(time), len(data[0][0:]), len(data[0][0])))
    for i in range(len(time) - 1):
        new_lat[i, :, :] = data[0]
        new_lon[i, :, :] = data[-1]
    return new_lat, new_lon


def create_dataset(data_object, param_name) -> xr.Dataset:
    lat, lon = expand_array_with_time_dimension(data_object.dtime, (data_object.latitudes, data_object.longitudes))
    ds = xr.Dataset(
        data_vars=dict(data=(["time", "x", "y"], data_object.data[1:, :, :])),
        coords=dict(lon=(["time", "x", "y"], lon[1:, :, :]),
                    lat=(["time", "x", "y"], lat[1:, :, :]),
                    time=data_object.dtime[1:]),
        attrs=dict(description="Basic weather param predictors for railtrack temperature forecast."),
    )
    ds = ds.rename(name_dict={'data': param_name})
    return ds


def add_data_to_dataset(data_object, param_name, ds) -> xr.Dataset:
    ds[param_name] = (["time", "x", "y"], data_object.data[1:, :, :])
    return ds


def sort_by_time_series(ds: xr.Dataset) -> xr.Dataset:
    ds = ds.sortby('time')
    return ds


def select_only_forecast_from_df(df):
    ds = df[1:]
    return ds


def mask_missing_data(data_object):
    data_object.data[~np.isfinite(data_object.mask_nodata)] = np.nan
    data_object.data[data_object.data == 9999] = np.nan
    return data_object


def calculate_forecast_period_dataset(times: np.array, df: xr.Dataset):
    forecast_period = []
    for i in range(len(times)):
        analysis_time = times[0]
        forecast_time = times[i]
        diff = forecast_time - analysis_time
        forecast_period.append(int(diff.days * 24 + diff.seconds / 3600))
    forecast_period = expand_array_with_domain(np.array(forecast_period), df["T2"].values)
    df['forecast_period'] = (["time", "x", "y"], np.array(forecast_period))
    return df


def calculate_hourly_values_dataset(data: np.array, name: str, df: xr.Dataset):
    param_new = np.zeros(shape=data.shape)
    period = list(df['forecast_period'].values[:, 0, 0])
    for i, time_step in enumerate(period):
        increment = 1
        if 90 <= int(time_step) < 144:
            increment = 3
        elif int(time_step) >= 144:
            increment = 6
        if i <= 0:
            param_new[i + 1] = (data[i + 1]) / 3600
            continue
        param_new[i + 1] = (data[i + 1] - data[i]) / (increment * 3600)
    df[name] = (["time", "x", "y"], param_new[1:])
    return df


def convert_percentage_to_zero_one(param_names: list, df: xr.Dataset) -> xr.Dataset:
    for name in param_names:
        df[name] = (["time", "x", "y"], df[name].values / 100)
    return df


def convert_kelvins_to_celsius(params_k: list, df: pd.DataFrame) -> pd.DataFrame:
    for param in params_k:
        df[param] = df[param] - 273.15
    return df


def calculate_wind_speed(df):
    df['WS'] = np.sqrt(df['U-MS'].values**2 + np.sqrt(df['V-MS'].values**2))
    return df


def calculate_angle_time_dataset(times: np.array, df: xr.Dataset) -> xr.Dataset:
    angles = {
        'sinhour': np.array([np.round((np.sin((ftime.hour*2*np.pi) / 24)), 2) for ftime in times]),
        'coshour':  np.array([np.round((np.cos((ftime.hour * 2 * np.pi) / 24)), 2) for ftime in times]),
        'sinmonth': np.array([np.round((np.sin((ftime.month * 2 * np.pi) / 12)), 2) for ftime in times]),
        'cosmonth': np.array([np.round((np.cos((ftime.month * 2 * np.pi) / 12)), 2) for ftime in times]),
        'month': np.array([ftime.month for ftime in times])
    }

    domain_values = df["T2"].values
    for key, angle_values in angles.items():
        expanded_values = expand_array_with_domain(angle_values, domain_values)
        df[key] = (["time", "x", "y"], expanded_values)
    return df


def expand_array_with_domain(data: np.array, array_origin):
    new_data = np.zeros(shape=array_origin.shape)
    for i in range(len(data) - 1):
        new_data[i] = np.tile(data[i+1], array_origin[0].shape)
    return new_data


def convert_timestr_datetime(df):
    date_format = '%Y%m%dT%H%M%S'
    times = df['time'].values
    df['time'] = [dt.strptime(t, date_format) for t in times]
    return df


def generate_sorter(times: np.array) -> np.array:
    return times.argsort()


def sort_array_by_time_series(data: np.array, sorter: np.array):
    data = data[sorter]
    return data


def select_forecast_params(df):
    df_variables = ['lat', 'lon', 'forecast_period', 'T2', 'D2', 'SKT', 'T_925', 'WS',
                    'LCC', 'MCC', 'sinhour', 'coshour', 'sinmonth', 'cosmonth',
                    'SRR1h', 'STR1h', 'month']
    forecast_params = df.loc[:, df_variables]
    return forecast_params


def select_forecast_params_old(df):
    df_variables = ['lat', 'lon', 'forecast_period', 'T2', 'D2', 'SKT', 'T_925', 'WS',
                    'LCC', 'MCC', 'sinhour', 'coshour', 'sinmonth', 'cosmonth',
                    'hourly_SRR', 'hourly_STR', 'month']
    forecast_params = df.loc[:, df_variables]
    return forecast_params


def read_csv_file(csv_file: str):
    return pd.read_csv(csv_file, sep=' ')


def rename_dataframe_columns(df):
    df.rename(columns={"T-K": "T2",
                       "TD-K": "D2",
                       "SKT-K": "SKT",
                       "T-K:::2:92500:1": "T_925",
                       "NL-0TO1": "LCC",
                       "NM-0TO1": "MCC",
                       "RNETSWA-JM2": "SRR1h",
                       "RNETLWA-JM2": "STR1h"}, inplace=True)
    return df


def rename_dataframe_columns_old(df):
    df.rename(columns={"T-K": "T2",
                       "TD-K": "D2",
                       "SKT-K": "SKT",
                       "T-K:::2:92500:1": "T_925",
                       "NL-0TO1": "LCC",
                       "NM-0TO1": "MCC",
                       "RNETSWA-JM2": "hourly_SRR",
                       "RNETLWA-JM2": "hourly_STR"}, inplace=True)
    return df


def calculate_forecast_period_dataframe(df):
    forecast_period = []
    for i in range(len(df['time'].values)):
        analysis_time = df['time'][0]
        forecast_time = df['time'][i]
        diff = forecast_time - analysis_time
        forecast_period.append(diff.days * 24 + diff.seconds / 3600)
    df.insert(3, 'forecast_period', forecast_period, True)
    return df


def calculate_hourly_values_dataframe(params: list, df):
    copy = df.copy()
    for param in params:
        param_data = df[param].values
        for i, time_step in enumerate(df['forecast_period'].values[:-1]):
            increment = 1
            if 90 <= time_step < 144:
                increment = 3
            elif time_step >= 144:
                increment = 6
            if i <= 0:
                df.at[i + 1, param] = (param_data[i + 1]) / 3600
                continue
            df.at[i + 1, param] = (param_data[i + 1] - copy[param].values[i]) / (increment * 3600)
    return df


def calculate_angle_time_dataframe(df):
    forecast_time = df['time']
    df['sinhour'] = [np.round((np.sin((ftime.hour*2*np.pi) / 24)), 2) for ftime in forecast_time]
    df['coshour'] = [np.round((np.cos((ftime.hour * 2 * np.pi) / 24)), 2) for ftime in forecast_time]
    df['sinmonth'] = [np.round((np.sin((ftime.month * 2 * np.pi) / 12)), 2) for ftime in forecast_time]
    df['cosmonth'] = [np.round((np.cos((ftime.month * 2 * np.pi) / 12)), 2) for ftime in forecast_time]
    df['month'] = [ftime.month for ftime in forecast_time]
    return df
