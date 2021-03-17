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
import pickle

geometry_lk_simplified = pd.read_pickle('./geometry_landkreise_simplified/geometry_lk_simplified_0_001.gzip')

now = datetime.datetime.now()
projection = gcrs.AlbersEqualArea()

df = pd.read_csv('all-series.csv')
df['Datum'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
sub = df[['Datum', 'Landkreis', 'InzidenzFallNeu_7TageSumme']]

start = datetime.datetime(2020, 3, 15)
end = datetime.datetime(2021, 3, 16)
index = pd.date_range(start, end)

def with_initializer(self, f_init):
    # Overwrite initializer hook in the Loky ProcessPoolExecutor
    # https://github.com/tomMoral/loky/blob/f4739e123acb711781e46581d5ed31ed8201c7a9/loky/process_executor.py#L850
    hasattr(self._backend, '_workers') or self.__enter__()
    origin_init = self._backend._workers._initializer
    def new_init():
        origin_init()
        f_init()
    self._backend._workers._initializer = new_init if callable(origin_init) else f_init
    return self

def _init_rasterio():
    import rasterio

def render_frame(day):
	sub_day = sub[sub['Datum'] == day]
	sub_day_merged = gpd.GeoDataFrame(sub_day.join(geometry_lk_simplified, on='Landkreis'))

	fig = plt.figure()
	ax = plt.subplot(projection=projection)
	ax.set_facecolor("#E8E8E8")
	ax.set_title('{:%d %B %Y}'.format(day))
	norm = mpl.colors.Normalize(vmin=1, vmax=300)
	gax3 = gplt.choropleth(sub_day_merged, hue='InzidenzFallNeu_7TageSumme', cmap='gist_heat_r', 
	                       extent=sub_day_merged.total_bounds, norm=norm, edgecolor='white', ax=ax, projection=projection)

	buf = io.BytesIO()
	plt.savefig(buf, format='png', bbox_inches='tight')
	plt.close()
	return buf

#im = Image.open(render_frame(datetime.datetime(2021, 3, 12)))
#im.show()


frames = []
with Parallel(4, verbose=10) as p:
    for r in with_initializer(p, _init_rasterio)(delayed(render_frame)(day) for day in index):
        frames.append(r)


#with open('animation_frames.pickle', 'wb') as f:
#	pickle.dump(frames, f)

im = Image.open(frames[0])
im.save('./animation/out.gif', save_all=True, duration=100, loop=0, append_images=[ Image.open(i) for i in frames[1:]])
