from eccodes import *
import sys
import time
import datetime
import numpy as np
import os
import fsspec
from tools import read_file_from_s3, sort_array_by_time_series, generate_sorter
import gc

GRIB_MESSAGE_STEP = None


class ReadData:
    def __init__(self, data_file: str,
                 added_hours: int = 0,
                 time_steps: int = 0,
                 read_coordinates: bool = False,
                 use_as_template: bool = False,
                 missing_data: bool = False):
        self.data_file = data_file
        self.data = None
        self.latitudes = None
        self.longitudes = None
        self.template = None
        self.dtime = None
        self.forecast_time = None
        self.analysis_time = None
        self.read(added_hours, read_coordinates, use_as_template, time_steps, missing_data)
        sorter = generate_sorter(self.dtime)
        self.dtime = sort_array_by_time_series(self.dtime, sorter)
        self.data = sort_array_by_time_series(self.data, sorter)

    def read(self, added_hours, read_coordinates, use_as_template, time_steps, missing_data):
        print(f"Reading {self.data_file}")
        if self.data_file.endswith(".grib2"):
            self.read_grib(added_hours, read_coordinates, use_as_template, time_steps, missing_data)
        else:
            sys.exit("unsupported file type for file: %s" % (self.data_file))

    def read_grib(self, added_hours, read_coordinates, use_as_template, time_steps, missing_data):
        global GRIB_MESSAGE_STEP
        start = time.time()

        def read_leadtime(gh):
            tr = codes_get_long(gh, "indicatorOfUnitOfTimeRange")
            ft = codes_get_long(gh, "forecastTime")
            if tr == 1:
                return datetime.timedelta(hours=ft)
            if tr == 0:
                return datetime.timedelta(minutes=ft)
            raise Exception("Unknown indicatorOfUnitOfTimeRange: {:%d}".format(tr))

        data_ls = []
        latitudes_ls = []
        longitudes_ls = []
        dtime_ls = []
        wrk_data_file = self.data_file

        if self.data_file.startswith("s3://"):
            wrk_data_file = read_file_from_s3(self.data_file)
            
        with open(wrk_data_file) as fp:
            while True:
                gh = codes_grib_new_from_file(fp)
                if gh is None:
                    break

                ni = codes_get_long(gh, "Ni")
                nj = codes_get_long(gh, "Nj")
                data_date = codes_get_long(gh, "dataDate")
                data_time = codes_get_long(gh, "dataTime")
                lt = read_leadtime(gh)
                self.analysis_time = datetime.datetime.strptime("{:d}/{:04d}".format(data_date, data_time), "%Y%m%d/%H%M")
                self.forecast_time = datetime.datetime.strptime("{:d}/{:04d}".format(data_date, data_time), "%Y%m%d/%H%M") + lt
                dtime_ls.append(self.forecast_time)
                values = np.asarray(codes_get_values(gh))
                data_ls.append(values.reshape(nj, ni))
                if read_coordinates:
                    latitudes_ls.append(np.asarray(codes_get_array(gh, "latitudes").reshape(nj, ni)))
                    longitudes_ls.append(np.asarray(codes_get_array(gh, "longitudes").reshape(nj, ni)))

                if use_as_template:
                    self.template = codes_clone(gh)
                    if GRIB_MESSAGE_STEP is None and lt > datetime.timedelta(minutes=0):
                        GRIB_MESSAGE_STEP = lt
                if codes_get_long(gh, "numberOfMissing") == ni*nj and missing_data is False:
                    print("File {} leadtime {} contains only missing data!".format(self.data_file, lt))
                    sys.exit(1)

                codes_release(gh)

                if len(dtime_ls) > time_steps:
                    fp.close()
                    del fp
                    del gh
                    gc.collect()
                    break

        self.data = np.asarray(data_ls)
        if len(latitudes_ls) > 0:
            self.latitudes = np.asarray(latitudes_ls)
            self.longitudes = np.asarray(longitudes_ls)
            self.latitudes = self.latitudes[0, :, :]
            self.longitudes = self.longitudes[0, :, :]

        mask_nodata = np.ma.masked_where(self.data == 9999, self.data)
        if type(dtime_ls) == list:
            self.dtime = np.array([(i+datetime.timedelta(hours=added_hours)) for i in dtime_ls])
        print("Read {} in {:.2f} seconds".format(self.data_file, time.time() - start))


class WriteData:
    def __init__(self, interpolated_data,
                 input_meta,
                 output_file: str,
                 write_option: str,
                 t_diff: int = 0,
                 time_series = None):  #TODO: Pitää olla ehkä 1h, koska analyysiä tässä ei ole mukana
        self.interpolated_data = interpolated_data
        self.t_diff = t_diff
        self.write_option = write_option
        self.template = input_meta
        self.time_series = time_series
        self.write(output_file)

    def write(self, output_file):
        if self.write_option == "s3":
            openfile = fsspec.open(
                "simplecache::{}".format(output_file),
                "wb",
                s3={
                    "anon": False,
                    "key": os.environ["S3_ACCESS_KEY_ID"],
                    "secret": os.environ["S3_SECRET_ACCESS_KEY"],
                    "client_kwargs": {"endpoint_url": "https://routines-data.lake.fmi.fi"},
                },
            )
            with openfile as fpout:
                self.write_grib_message(fpout)
        else:
            with open(output_file, "wb") as fpout:
                self.write_grib_message(fpout)
        print("wrote file '%s'" % output_file)

    def write_grib_message(self, fp):
        dataDate = int(codes_get_long(self.template, "dataDate"))
        dataTime = int(codes_get_long(self.template, "dataTime"))
        analysistime = datetime.datetime.strptime("{}{:04d}".format(dataDate, dataTime), "%Y%m%d%H%M")
        analysistime = analysistime + datetime.timedelta(hours=self.t_diff)
        codes_set_long(self.template, "dataDate", int(analysistime.strftime("%Y%m%d")))
        codes_set_long(self.template, "dataTime", int(analysistime.strftime("%H%M")))
        codes_set_long(self.template, "bitsPerValue", 24)
        codes_set_long(self.template, "generatingProcessIdentifier", 202)
        codes_set_long(self.template, "centre", 86)
        codes_set_long(self.template, "bitmapPresent", 1)
        codes_set_long(self.template, "indicatorOfUnitOfTimeRange", 0)  # minute
        codes_set_long(self.template, "stepUnits", 1)  # minute
        base_lt = datetime.timedelta(minutes=15)
        pdtn = codes_get_long(self.template, "productDefinitionTemplateNumber")
        for i in range(self.interpolated_data.shape[0]):
            lt = base_lt * i
            if self.time_series is not None:
                lt = self.time_series[i] - self.time_series[0]
            if pdtn == 8:
                lt -= base_lt

                tr = codes_get_long(self.template, "indicatorOfUnitForTimeRange")
                trlen = codes_get_long(self.template, "lengthOfTimeRange")

                assert ((tr == 1 and trlen == 1) or (tr == 0 and trlen == 60))
                lt_end = analysistime + datetime.timedelta(
                    hours=codes_get_long(self.template, "lengthOfTimeRange"))

                # these are not mandatory but some software uses them
                codes_set_long(self.template, "yearOfEndOfOverallTimeInterval", int(lt_end.strftime("%Y")))
                codes_set_long(self.template, "monthOfEndOfOverallTimeInterval", int(lt_end.strftime("%m")))
                codes_set_long(self.template, "dayOfEndOfOverallTimeInterval", int(lt_end.strftime("%d")))
                codes_set_long(self.template, "hourOfEndOfOverallTimeInterval", int(lt_end.strftime("%H")))
                codes_set_long(self.template, "minuteOfEndOfOverallTimeInterval", int(lt_end.strftime("%M")))
                codes_set_long(self.template, "secondOfEndOfOverallTimeInterval", int(lt_end.strftime("%S")))

            codes_set_long(self.template, "forecastTime", lt.total_seconds() / 60)
            codes_set_values(self.template, self.interpolated_data[i, :, :].flatten())
            codes_write(self.template, fp)

        print("")
        codes_release(self.template)
        fp.close()
