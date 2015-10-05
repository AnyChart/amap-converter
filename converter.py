#!/usr/bin/python

import zipfile
import struct
import shapefile

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
    
    print "Data table: (key, name)"
    for _ in range(0, columns_count):
        col = {}
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
        
        for _ in range(0, columns_count - 1):
            column = {}
            (c, offset) = read_string(bytes, offset)
            group['columns'].append(c)

        (is_transformed, offset) = read_bool(bytes, offset)
        if is_transformed:
            group['transformation'] = {}
            (group['transformation']['dx'], offset) = read_double(bytes, offset)
            (group['transformation']['dy'], offset) = read_double(bytes, offset)
            (group['transformation']['sx'], offset) = read_double(bytes, offset)
            (group['transformation']['sy'], offset) = read_double(bytes, offset)

        group['label_pt'] = {}
        (group['label_pt']['lat'], offset) = read_double(bytes, offset)
        (group['label_pt']['long'], offset) = read_double(bytes, offset)

        group['polygons'] = []
        (polygons, offset) = read_int(bytes, offset)
        print "Polygons count:", polygons
        for _ in range(0, polygons):
            poly = []
            (pts, offset) = read_int(bytes, offset)
            for _ in range(0, pts):
                (p_long, offset) = read_double(bytes, offset)
                (p_lat, offset) = read_double(bytes, offset)
                poly.append({"lat": p_lat,
                             "long": p_long})
            group['polygons'].append(poly)
        amap['groups'].append(group)
    return amap

def write_shp(amap, path):
    w = shapefile.Writer()
    for group in amap['groups']:
        for poly in group['polygons']:
            w.poly(parts=[])
            w.record('Create', 'Polygon')
    w.save()

print read_amap('states.amap')
