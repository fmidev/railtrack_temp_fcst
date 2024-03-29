import argparse
import tools as tl
from file_utils import ReadData, WriteData


def main():
    """Rail trail temperature forecast

    This program creates...

    """
    data, data_meta, ds = [], [], []
    args = parse_command_line()
    forecast_params = tl.fetch_basic_predictor_files(args)
    for i, (param_name, param_file) in enumerate(forecast_params.items()):
        if param_name == 'SKT':
            data_meta = ReadData(param_file, use_as_template=True, read_coordinates=True)
        if i == 0:
            data = ReadData(param_file, read_coordinates=True, time_steps=125)
            data = tl.mask_missing_data(data)
            ds = tl.create_dataset(data, param_name)
            ds = tl.calculate_forecast_period_dataset(data.dtime, ds)
            continue
        if param_name == 'SRR1h' or param_name == 'STR1h':
            data_rad = ReadData(param_file, time_steps=125, missing_data=True)
            data_rad = tl.mask_missing_data(data_rad)
            #TODO: tarkasta toimiiko maskin kanssa
            ds = tl.calculate_hourly_values_dataset(data_rad.data, param_name, ds)
            continue
        data = ReadData(param_file, time_steps=125)
        data = tl.mask_missing_data(data)
        ds = tl.add_data_to_dataset(data, param_name, ds)
    ds = tl.calculate_angle_time_dataset(data.dtime, ds)
    ds = tl.convert_percentage_to_zero_one(['LCC', 'MCC'], ds)
    ML_model = tl.load_ML_model(args.ML_model)
    t_trail_fcst = tl.generate_ML_forecast_domain(ds, ML_model, data.data[1:])
    WriteData(t_trail_fcst, data_meta.template, args.output_file,
              's3' if args.output_file.startswith('s3://') else 'local',
              time_series=data.dtime[1:])


def parse_command_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument("--T2", action="store", type=str, required=True)
    parser.add_argument("--D2", action="store", type=str, required=True)
    parser.add_argument("--SKT", action="store", type=str, required=True)
    parser.add_argument("--T_925", action="store", type=str, required=True)
    parser.add_argument("--WS", action="store", type=str, required=True)
    parser.add_argument("--LCC", action="store", type=str, required=True)
    parser.add_argument("--MCC", action="store", type=str, required=True)
    parser.add_argument("--SRR1h", action="store", type=str, required=True)
    parser.add_argument("--STR1h", action="store", type=str, required=True)
    parser.add_argument("--ML_model", action="store", type=str, required=True)
    parser.add_argument("--output_file", action="store", type=str, required=True)
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    main()
