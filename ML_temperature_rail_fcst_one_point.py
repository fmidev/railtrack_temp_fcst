import argparse
import tools as tl

def main():
    args = parse_command_line()
    df = tl.read_csv_file(args.input_file)
    df = tl.rename_dataframe_columns(df)
    df = tl.convert_timestr_datetime(df)
    df = tl.calculate_forecast_period_dataframe(df)
    #df = tl.convert_kelvins_to_celsius(["T2", "D2", "SKT", "T_925"], df)
    df = tl.calculate_wind_speed(df)
    df = tl.calculate_hourly_values_dataframe(["SRR1h", "STR1h"], df)
    df = tl.select_only_forecast_from_df(df)
    df = tl.calculate_angle_time_dataframe(df)
    ML_df = tl.select_forecast_params(df)
    ML_model = tl.load_ML_model(args.ML_model)
    t_trail_fcst = ML_model.predict(ML_df.values)
    t_trail_fcst = t_trail_fcst - 273.15
    print("homma done")
    # TODO: jotain plottailua voisi tehdä


def parse_command_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument("--input_file", action="store", type=str, required=True)
    parser.add_argument("--ML_model", action="store", type=str, required=True)
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    main()