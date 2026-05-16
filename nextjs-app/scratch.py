import urllib.request
import gzip
import mapbox_vector_tile

url = "https://tiles.openfreemap.org/planet/5/19/10.pbf"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
response = urllib.request.urlopen(req)
data = response.read()

try:
    data = gzip.decompress(data)
except Exception:
    pass

tile = mapbox_vector_tile.decode(data)
boundary_layer = tile.get('boundary')
if boundary_layer:
    for feature in boundary_layer['features']:
        props = feature['properties']
        if props.get('admin_level') in [3, 4]:
            print(props)
else:
    print("No boundary layer")
