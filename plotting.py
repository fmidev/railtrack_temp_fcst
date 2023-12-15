import os
import argparse
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime as dt
from datetime import timedelta as td
from mpl_toolkits.basemap import Basemap
import cartopy
from file_utils import ReadData


def main():
    pwd = os.getcwd()
    pwd = os.path.split(pwd)[0]
    fig_out = f"{pwd}/rail_temperature/figures/"
    if os.path.isdir(fig_out) is False:
        os.mkdir(fig_out)

    args = parse_command_line()
    data = ReadData(args.input_file, read_coordinates=True,  time_steps=125)
    plot_NWC_data_imshow_polster(data, fig_out, "Railtrack temperature forecast from EC")


def plot_NWC_data_imshow_polster(data, outfile, title, vmin=-10, vmax=5):
    """Use for plotting when projection is Polster/Polar_stereografic

    Only for Scandinavian domain. For other domains coordinates must be changed.
    """
    cmap = matplotlib.cm.coolwarm       #"coolwarm", 'RdBl_r'  'Blues' 'Jet' 'RdYlGn_r'
    lon = data.longitudes
    lat = data.latitudes
    fig_date = data.analysis_time

    vmin = 5 * round(int(np.min(data.data - 273.15) - 2) / 5)
    vmax = 5 * round(int(np.max(data.data - 273.15) + 2) / 5)
    zero_point = (abs(vmin)/(abs(vmin) + abs(vmax)))
    s_cmap = shiftedColorMap(cmap, midpoint=zero_point, name='shifted')

    for i in range(len(data.data)):
        hour = 0
        fig, ax = plt.subplots(1, 1, figsize=(16, 12))
        if i > 0:
            hour = (data.dtime[i] - data.dtime[0]).total_seconds() / 3600
            fig_date = data.dtime[i]
        m = Basemap(width=970000, height=1300000,
                    resolution='i', rsphere=(6378137.00,6356752.3142),
                    projection='lcc', ellps='WGS84',
                    lat_1=64.8, lat_2=64.8, lat_0=64.8, lon_0=26.0, ax=ax)
        m.drawcountries(linewidth=1.0)
        m.drawcoastlines(1.0)
        d = data.data[i, :, :] - 273.15
        d[0, 0] = vmin
        d[-1, -1] = vmax
        x, y = m(lon, lat)

        if i == 0:
            # Koulutukseen käytetyt koordinaatit:
            lat_obs = [62.39783, 61.838333, 60.90774, 63.891666, 61.28091, 61.044735,
                       62.48737, 64.87932, 64.55291, 60.90785, 66.14115]
            lon_obs = [30.027159, 25.111172, 27.283697, 23.854307, 23.750443, 26.73692,
                       27.195679, 25.503368, 27.160814, 27.285547, 24.921642]
            cm = m.pcolormesh(x, y, d, cmap=s_cmap)
            #m.scatter(lon_obs, lat_obs, zorder=1, alpha=0.8, c='k', s=56, latlon=True)
            #m.scatter(lon_obs, lat_obs, zorder=2, alpha=0.8, c='g', s=26, latlon=True)
        else:
            cm = m.pcolormesh(x, y, d, cmap=s_cmap)
        analysis = data.analysis_time - td(hours=int(1))
        plt.title(f"{title} {dt.strftime(fig_date, '%Y-%m-%d %H:%M')},\n Analysistime {analysis}, forecast + {int(hour) + 1}h)")
        plt.colorbar(cm, fraction=0.033, pad=0.04, orientation="horizontal")
        forecast_outfile = outfile + f"{dt.strftime(data.analysis_time, '%Y%m%d%H%M')}_TRAIL_fcst+{int(hour) + 1}h.png"
        plt.savefig(forecast_outfile, dpi=300, bbox_inches='tight', pad_inches=0.2)
        plt.close()


def generate_fig(proj):
    ax = plt.axes(projection=proj)
    ax.set_extent([0, 39, 51, 73])
    ax.gridlines()
    ax.add_feature(cartopy.feature.COASTLINE)
    ax.add_feature(cartopy.feature.BORDERS)
    ax.add_feature(cartopy.feature.OCEAN)
    ax.add_feature(cartopy.feature.LAND)
    return ax


def parse_command_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument("--input_file", action="store", type=str, required=True)
    args = parser.parse_args()
    return args


def shiftedColorMap(cmap, start=0, midpoint=0.5, stop=1.0, name='shiftedcmap'):
    cdict = {
        'red': [],
        'green': [],
        'blue': [],
        'alpha': []
    }
    # regular index to compute the colors
    reg_index = np.linspace(start, stop, 257)
    # shifted index to match the data
    shift_index = np.hstack([
        np.linspace(0.0, midpoint, 128, endpoint=False),
        np.linspace(midpoint, 1.0, 129, endpoint=True)
    ])
    for ri, si in zip(reg_index, shift_index):
        r, g, b, a = cmap(ri)
        cdict['red'].append((si, r, r))
        cdict['green'].append((si, g, g))
        cdict['blue'].append((si, b, b))
        cdict['alpha'].append((si, a, a))

    newcmap = matplotlib.colors.LinearSegmentedColormap(name, cdict)
    plt.register_cmap(cmap=newcmap)

    return newcmap


if __name__ == '__main__':
    main()
