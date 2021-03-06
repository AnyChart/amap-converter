#!/usr/bin/python

import zipfile
import struct
import shapefile
import sys
import json
import os

def read_zip(path):
    with zipfile.ZipFile(path, 'r') as myzip:
        return myzip.read('map.bin')

def read_int(bytes, offset):
    return (struct.unpack_from('i', bytes, offset)[0], offset + 4)

def read_string(bytes, offset):
    str_len = struct.unpack_from('i', bytes, offset)[0]
    return (struct.unpack_from(str(str_len) + 's', bytes, offset + 4)[0].decode('utf-8'), offset + 4 + str_len)

def read_bool(bytes, offset):
    return (struct.unpack_from('?', bytes, offset)[0], offset + 1)

def read_byte(bytes, offset):
    return (struct.unpack_from('b', bytes, offset)[0], offset + 1)

def read_double(bytes, offset):
    return (struct.unpack_from('d', bytes, offset)[0], offset + 8)

def read_amap(path):
    amap = {}
    bytes = read_zip(path)
    (amap['version'], offset) = read_string(bytes, 0)
    (amap['is_world'], offset) = read_bool(bytes, offset)
    (amap['default_projection'], offset) = read_string(bytes, offset)
    
    (columns_count, offset) = read_byte(bytes, offset)

    columns = []
    
    for _ in range(0, columns_count):
        col = {'max_len': 0}
        (col['is_key'], offset) = read_bool(bytes, offset)
        (col['name'], offset) = read_string(bytes, offset)
        columns.append(col)

    amap['bounds'] = {}
    (amap['bounds']['min_long'], offset) = read_double(bytes, offset)
    (amap['bounds']['max_lat'], offset) = read_double(bytes, offset)
    (amap['bounds']['max_long'], offset) = read_double(bytes, offset)
    (amap['bounds']['min_lat'], offset) = read_double(bytes, offset)

    amap['groups'] = [];
    (groups_count, offset) = read_int(bytes, offset)
    for _ in range(0, groups_count):
        group = {'columns': []}
        
        (group['name'], offset) = read_string(bytes, offset)
        
        column = columns[0]
        column['max_len'] = max(column['max_len'], len(group['name'].encode('utf-8')))
        group['columns'].append(group['name'])
        
        for idx in range(0, columns_count - 1):
            column = columns[idx+1]
            (c, offset) = read_string(bytes, offset)
            column['max_len'] = max(column['max_len'], len(c.encode('utf-8')))
            group['columns'].append(c)

        (is_transformed, offset) = read_bool(bytes, offset)
        if is_transformed:
            group['transformation'] = {}
            (group['transformation']['dx'], offset) = read_double(bytes, offset)
            (group['transformation']['dy'], offset) = read_double(bytes, offset)
            (group['transformation']['sx'], offset) = read_double(bytes, offset)
            (group['transformation']['sy'], offset) = read_double(bytes, offset)
            print "WARN: transformations not supported", group["name"]

        group['label_pt'] = {}
        (group['label_pt']['lat'], offset) = read_double(bytes, offset)
        (group['label_pt']['long'], offset) = read_double(bytes, offset)

        group['polygons'] = []
        (polygons, offset) = read_int(bytes, offset)
        for _ in range(0, polygons):
            poly = []
            (pts, offset) = read_int(bytes, offset)
            for _ in range(0, pts):
                (p_long, offset) = read_double(bytes, offset)
                (p_lat, offset) = read_double(bytes, offset)
                poly.append({"lat": - p_lat,
                             "long": p_long})
            
            group['polygons'].append(poly)
        amap['groups'].append(group)
    amap['columns'] = columns
    return amap

def write_shp(amap, path):
    w = shapefile.Writer(shapefile.POLYGON)
    w.autoBalance = 1
    for c in amap['columns']:
        w.field(c['name'].encode('utf-8'), 'C', c['max_len'])
    w.field('latitude', 'F')
    w.field('longitude', 'F')

    for group in amap['groups']:
        w.poly(parts=map(lambda poly: map(lambda pt: [pt['long'], pt['lat']], poly), group['polygons']))
        w.record(*(group['columns'] + [ -group['label_pt']['lat'], group['label_pt']['long']]))
    w.save(path)

def generate_geojson(amap):
    features = []
    for group in amap['groups']:
        props = {}
        for idx,c in enumerate(amap["columns"]):
            props[c['name']] = group["columns"][idx]
        props["label_lat"] = -group['label_pt']['lat']
        props["label_lon"] = group['label_pt']['long']
        coords = map(lambda poly: [map(lambda pt: [pt['long'], pt['lat']], poly)], group['polygons'])
        geometry = {"type": "MultiPolygon", "coordinates": coords}
        features.append({"type":"Feature", "properties": props, "geometry": geometry})
        
    return {"type": "FeatureCollection",
            "features": features}

def write_geojson(geojson, path):
    with open(path + ".json", 'w') as outfile:
        json.dump(geojson, outfile)

def write_mapjs(map_name, geojson, path):
    with open(path + ".js", 'w') as outfile:
        outfile.write("window['anychart']=window['anychart']||{};window['anychart']['maps']=window['anychart']['maps']||{};window['anychart']['maps']['"+map_name+"']=" + json.dumps(geojson))

def write_map_sample(map_name, path):
    with open(path + ".html", 'w') as outfile:
        outfile.write("""<!doctype html>
<html>
  <head>
    <script type='text/javascript' src='http://cdn.anychart.com/js/latest/anymap.min.js'></script>
    <script type='text/javascript' src='./{0}.js'></script>
    <style type='text/css'>
        html, body, #container {{ width: 100%; height: 100%; margin: 0; padding: 0; }}
    </style>
  </head>
  <body>
    <div id='container'></div>
    <script>
    anychart.onDocumentReady(function() {{
      // create map
      map = anychart.map();
      map.geoData(anychart.maps['{0}']);
      map.container('container');
      map.draw();
    }});
    </script>
  </body>
</html>""".format(map_name))
        
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "Usage: converter src.amap dest-base-name"
    else:
        amap = read_amap(sys.argv[1])
        out = sys.argv[2]
        geojson = generate_geojson(amap)
        write_shp(amap, out)
        write_geojson(geojson, out)
        write_mapjs(os.path.basename(out), geojson, out)
        write_map_sample(os.path.basename(out), out)
