import rasterio
import pandas as pd
import geopandas as gpd
from matplotlib import pyplot as plt
from matplotlib import colors
import matplotlib as mpl
import geoplot as gplt
import geoplot.crs as gcrs
import datetime
import io
from PIL import Image
from joblib import Parallel, delayed
import argparse
import multiprocessing
from pathlib import Path


def with_initializer(self, f_init):
	"""Quick hack to first call a initializer before worker processes will execute the given job,
	this is neccessary on my current native Apple M1 environment (rasterio libaery must import first)
	
	solution from: https://stackoverflow.com/questions/55424095/error-pickling-a-matlab-object-in-joblib-parallel-context/55566003#55566003
	Overwrite initializer hook in the Loky ProcessPoolExecutor
	https://github.com/tomMoral/loky/blob/f4739e123acb711781e46581d5ed31ed8201c7a9/loky/process_executor.py#L850
	"""
	hasattr(self._backend, '_workers') or self.__enter__()
	origin_init = self._backend._workers._initializer
	def new_init():
		origin_init()
		f_init()
	self._backend._workers._initializer = new_init if callable(origin_init) else f_init
	return self


def _init_rasterio():
	"""initializer for workers"""
	import rasterio


def render_frame(day):
	"""generates a choropleth map for a given day. 
	   returns a file like object or None
	"""
	sub_day = sub[sub['Datum'] == day]
	sub_day_merged = gpd.GeoDataFrame(sub_day.join(geometry_lk_simplified, on='Landkreis'))
	sub_day_merged = sub_day_merged[sub_day_merged.geometry != None]  # remove rows without a geometry (Bund, Länder)
	fig = plt.figure(figsize=args.size)  # with plt.figure(figsize=(7,10)) figure dimension can be given
	ax = plt.subplot(projection=projection)
	ax.set_facecolor("#E8E8E8")  # background color of the figure
	ax.set_title('{:%d %B %Y}'.format(day))  # tile of plot
	gax = gplt.choropleth(sub_day_merged, hue=args.column, cmap=args.cmap, 
						   extent=sub_day_merged.total_bounds, norm=norm, edgecolor=args.edge_color, ax=ax, projection=projection)
	buf = io.BytesIO()
	plt.savefig(buf, format=args.file_format, bbox_inches='tight')  # save figure to a new file object
	plt.close()  # importent: close the figure objet at the end, it will free the memory resources used by matblotlib
	
	if not args.maps_only:
		return buf
	else:
		with open("./frames/{:%Y-%m-%d}.{}".format(day, args.file_format), "wb") as fd:
			fd.write(buf.getbuffer())
		return


def size_str(size_str):
	return tuple(map(lambda x : float(x), size_str.upper().split('X')))



if __name__ == "__main__":
	supported_file_formats = list(plt.gcf().canvas.get_supported_filetypes().keys())
	parser = argparse.ArgumentParser(description="""
		renders a animated choropleth map for a given persiod""")
	parser.add_argument('-s', '--start', help="start of period for generating maps", type=datetime.date.fromisoformat, default="2021-02-01")
	parser.add_argument('-e', '--end', help="end of period for generating maps", type=datetime.date.fromisoformat, default="2021-03-16")
	parser.add_argument('-d', '--data', help="csv which is used to render the map", type=str, default="../all-series.csv")
	parser.add_argument('--size', help="size of generated maps in inch e.g 6x8", type=size_str, default="6.0X8.0")
	parser.add_argument('--column', help='csv column which is used to generate maps', type=str, default="InzidenzFallNeu_7TageSumme")
	parser.add_argument('--cmap', help=
		'matplotlib colormap (must be one of supported colors, look at https://matplotlib.org/stable/tutorials/colors/colormaps.html?highlight=colormap)', 
		type=str, default="gist_heat_r")
	parser.add_argument('--edge_color', help=
		'color of county lines', type=str, default="white")
	parser.add_argument('--vmin', help=
		'lowest value that is mapped to a color (this paramter will have wield influence of the impression of the map)', type=int, default=1)
	parser.add_argument('--vmax', help=
		'highest value that is mapped to a color (this paramter will have wield influence of the impression of the map)', type=int, default=300)
	parser.add_argument('--duration', help='duration of a frame in milliseconds', type=int, default=100)
	parser.add_argument('-p', '--parallel', help="numbers of cpu cores to use", type=int, default=multiprocessing.cpu_count())
	parser.add_argument('--maps_only', help="instead of creating a animated gif, store all figures in ./frames/ folder", action='store_true')
	parser.add_argument('--file_format', choices=supported_file_formats, 
		help="file format for maps only mode", type=str, default="png")
	
	args = parser.parse_args()

	# geometry for counties
	geometry_lk_simplified = pd.read_pickle('../geometry_landkreise_simplified/geometry_lk_simplified_0_001.gzip')

	# choose projection for the map
	projection = gcrs.AlbersEqualArea()

	# normalize the values for the colormap
	norm = mpl.colors.Normalize(vmin=args.vmin, vmax=args.vmax)

	# data series with incidence
	df = pd.read_csv(args.data)
	df['Datum'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')

	# only select needed columns for speedup
	sub = df[['Datum', 'Landkreis', args.column]]

	# period of map generation
	period_index = pd.date_range(args.start, args.end)

	if args.maps_only:
		# create outputfolder for maps_only mode
		Path("./frames/").mkdir(parents=True, exist_ok=True)
	
	# debug code
	# render_frame(period_index[0])

	# generates maps for the period in parallel with joblib (https://joblib.readthedocs.io/en/latest/)
	frames = []
	with Parallel(args.parallel, verbose=10) as p:
		for r in with_initializer(p, _init_rasterio)(delayed(render_frame)(day) for day in period_index):
			frames.append(r)
	
	if not args.maps_only:
		im = Image.open(frames[0])
		gif_filename = './{}.gif'.format(args.column)
		im.save(gif_filename, save_all=True, duration=args.duration, loop=0, append_images=[ Image.open(i) for i in frames[1:]])
