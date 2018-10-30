#!/usr/bin/env python
# SCRIPT and process by Kyle Fitzsimmons, Edited by Marshall Davey
# TRIP LAB - Concordia University

# Reduces GTFS routes along a single path to a unique feature
import fiona
from fiona.crs import from_epsg
import math
import psycopg2
from shapely.geometry import LineString

# DB_CONF = {
#     'host': '127.0.0.1',  # ip needed for Windows/Linux subsystem
#     'user': 'postgres',
#     'password': 'postgres',
#     'dbname': 'montreal_gtfs'
# }
# INPUT_SHP_FN = "D:\mtl_roads_ests\dist_links_new.shp"
# INPUT_SHP_SRID = 32618
# RESULTS_NODES_SHP_FN = 'D:\mtl_roads_ests/nodes_kf30new.shp'
# RESULTS_SEGMENTS_SHP_FN = 'D:\mtl_roads_ests/unique_segments_kf30new.shp'
# out_name = "test"
# # conn = psycopg2.connect(**DB_CONF)
# # cur = conn.cursor()
# global db_cur
# global db_conn
# try:
#     db_conn = psycopg2.connect(user='postgres', host='localhost', password='postgres', port=5432,
#                                database='montreal_test')
#     db_cur = db_conn.cursor()
# except:
#     print "cannot connect"
#
# srid = 32618


    # Calculate the distance in meters between two UTM points

def pythagoras(point1, point2):
    a = point2[0] - point1[0]
    b = point2[1] - point1[1]
    d = math.sqrt(a**2 + b**2)
    return d


def drop_tables(cur,conn):
    drop_tables_sql = '''
        DROP TABLE IF EXISTS endpoints;
        DROP TABLE IF EXISTS links;
        DROP TABLE IF EXISTS endpoints_nearby_links;
    '''
    cur.execute(drop_tables_sql)
    conn.commit()


# def load_shp_links_to_postgis(cur,conn):
#     create_table_sql = '''
#         DROP TABLE IF EXISTS links;
#         CREATE TABLE links (
#             link_id INTEGER UNIQUE NOT NULL,
#             route_count INTEGER,
#             geom GEOMETRY(LINESTRING)
#         );
#     '''
#     cur.execute(create_table_sql)
#
#     with fiona.open(INPUT_SHP_FN, 'r') as links_f:
#         values = []
#         for link in links_f:
#             # remove links with same start and end coordinates
#             if link['geometry']['coordinates'][0] == link['geometry']['coordinates'][-1]:
#                 continue
#
#             linestring_coordinates = ', '.join(['{} {}'.format(*c) for c in link['geometry']['coordinates']])
#             values.append({
#                 'link_id': link['properties']['link_id'],
#                 #'route_count': link['properties']['route_coun'],
#                 'wkt': 'LINESTRING(' + linestring_coordinates + ')',
#                 'srid': INPUT_SHP_SRID
#             })
#
#         sql = '''
#             INSERT INTO links (link_id, geom)
#             VALUES (%(link_id)s, ST_GeomFromText(%(wkt)s, %(srid)s));
#         '''  # removed route count here
#         cur.executemany(sql, values)
#         conn.commit()


def load_endpoints_to_postgis(cur,conn):
    create_table_sql = '''
        DROP TABLE IF EXISTS endpoints;
        CREATE TABLE endpoints (
            id SERIAL PRIMARY KEY,
            link_id INTEGER NOT NULL,
            geom GEOMETRY(POINT)
        );        
    '''
    cur.execute(create_table_sql)

    start_points_sql = '''
        INSERT INTO endpoints (link_id, geom)
        SELECT link_id, ST_StartPoint(link_geom) AS geom
        FROM distinct_links;
        
    '''
    cur.execute(start_points_sql)

    end_points_sql = '''
        INSERT INTO endpoints (link_id, geom)
        SELECT link_id, ST_EndPoint(link_geom) AS geom
        FROM distinct_links;
        
    '''
    cur.execute(end_points_sql)
    conn.commit()


def create_input_data_indexes(cur,conn):
    create_index_sql = '''
        CREATE INDEX IF NOT EXISTS endpoints_geom_idx ON endpoints USING GIST (geom);
        CREATE INDEX IF NOT EXISTS links_geom_idx ON distinct_links USING GIST (link_geom);
    '''
    cur.execute(create_index_sql)
    conn.commit()


def find_endpoint_intersections_with_links(cur,conn):
    create_table_sql = '''
        DROP TABLE IF EXISTS endpoints_nearby_links;
        CREATE TABLE endpoints_nearby_links (
            endpoint_id INTEGER NOT NULL,
            link_id INTEGER NOT NULL
        );
    '''
    cur.execute(create_table_sql)

    nearby_links_sql = '''
        INSERT INTO endpoints_nearby_links
        SELECT endpoints.id AS endpoint_id, distinct_links.link_id
        FROM endpoints, distinct_links
        WHERE ST_DWithin(endpoints.geom, distinct_links.link_geom, 0.4);
    '''
    cur.execute(nearby_links_sql)
    conn.commit()


def fetch_collapsed_nodes(cur,conn):
    nodes = {}

    clustered_nodes_sql = '''
        SELECT cluster_id,
               MIN(clusters.endpoint_id) AS node_id,
               ARRAY_AGG(clusters.endpoint_id) AS nearby_nodes,
               ST_AsText(ST_Centroid(clusters.geom)) AS wkt
        FROM (
            SELECT id AS endpoint_id,
                   geom,
                   ST_ClusterDBSCAN(geom, 1, 2) OVER() AS cluster_id
            FROM endpoints
        ) clusters
        GROUP BY cluster_id, geom
        ORDER BY node_id;
    '''
    cur.execute(clustered_nodes_sql)
    for cluster_id, node_id, nearby_nodes, wkt in cur.fetchall():
        nearby_nodes.remove(node_id)
        x, y = wkt.split('(')[1][:-1].split(' ')

        nodes[node_id] = {
            'nearby_nodes': nearby_nodes,
            'links': set(),
            'coordinates': (float(x), float(y))
        }

    nearby_links_sql = '''
        SELECT endpoint_id, link_id
        FROM endpoints_nearby_links;
    '''
    cur.execute(nearby_links_sql)
    endpoint_links = {}
    for endpoint_id, link_id in cur.fetchall():
        endpoint_links.setdefault(endpoint_id, set()).add(link_id)


    for node_id, node in nodes.items():
        node['links'].update(endpoint_links[node_id])

        for nearby_node_id in node['nearby_nodes']:
            node['links'].update(endpoint_links[nearby_node_id])
    return nodes

# maybe this should be done from using the original links
# data and searching for the root nodes by cluster
def generate_links_from_collapsed_nodes(nodes,cur,conn):
    links = {}
    for node_idx, node in nodes.items():
        for link_id in node['links']:
            if not link_id in links:
                links[link_id] = {
                    'coordinates': [node['coordinates']],
                    'nodes': [node_idx]
                }
            else:
                links[link_id]['coordinates'].append(node['coordinates'])
                links[link_id]['nodes'].append(node_idx)
    return links


# Iterating through all flattened links, find links with more than 2 nodes. If
# the node is not the existing line endpoint, cut the link into multiple
# link segments so that each each segment only has 2 coordinates (start and end nodes).
# Otherwise if link is already only two coordinates, this is a legitimate
# segment.
def cut_links_into_segments(nodes, links,cur,conn):
    segments = []
    for link_id, link in links.items():
        if len(link['nodes']) > 2:
            node_pairs = []
            seen = []
            # pair the node order by shortest distances. Assumption is that
            # first node is always endpoint original shapefile line (double-check)
            for node_idx in link['nodes']:
                closest_distance = 10 ** 20
                closest_node_idx = None
                for test_node_idx in link['nodes']:
                    if test_node_idx == node_idx:
                        continue

                    distance = pythagoras(nodes[node_idx]['coordinates'],
                                          nodes[test_node_idx]['coordinates'])
                    # if link_id == 84595:
                    #     print(node_idx, test_node_idx, distance, closest_distance, distance < closest_distance)
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_node_idx = test_node_idx

                if ((node_idx, closest_node_idx) not in node_pairs and (closest_node_idx, node_idx)) not in node_pairs:
                    node_pairs.append((node_idx, closest_node_idx))


            for pair_idx, pair in enumerate(node_pairs, start=1):
                start_node_idx, end_node_idx = pair
                cut_segment = dict(link)
                cut_segment['link_id'] = link_id
                cut_segment['segment_id'] = '{link_id}-{segment_id}'.format(link_id=link_id,
                                                                            segment_id=pair_idx)
                cut_segment['nodes'] = list(pair)
                cut_segment['coordinates'] = [nodes[start_node_idx]['coordinates'], nodes[end_node_idx]['coordinates']]
                segments.append(cut_segment)

        elif len(link['nodes']) == 2:
            link['link_id'] = link_id
            link['segment_id'] = link_id
            segments.append(link)

        else:
            print(link_id, link)
            # raise Exception('Link has less than 2 coordinates.')
    return segments


def remove_duplicate_segments(segments,cur,conn):
    unique_segments = []
    seen_node_pairs = set()
    for segment in segments:
        node_pair = tuple(segment['nodes'])
        node_pair_reverse = tuple(reversed(segment['nodes']))
        if node_pair not in seen_node_pairs:
            unique_segments.append(segment)
            seen_node_pairs.add(node_pair)
            seen_node_pairs.add(node_pair_reverse)
    return unique_segments

def write_unique_segments_to_postgres(out_name, unique_segments, srid,cur,conn):
    make_segment_table = """
        DROP TABLE IF EXISTS {out_name};
        CREATE TABLE {out_name} (link_id integer, segment_id character varying(20), new_id integer, link_geom geometry);"""

    try:
        cur.execute(make_segment_table.format(out_name=out_name))
        conn.commit()
    except psycopg2.Error as e:
        print e.pgcode
        print e.pgerror
        raise e

    make_links = """
       INSERT INTO {out_name} (link_id, segment_id, new_id, link_geom)
       VALUES ( {link_id}, {segment_id}, {new_id}, (ST_GeomFromText(('{line}'), {srid})) ) ;

       """
    counter = 0
    for item in unique_segments:
        link_id = item['link_id']
        segment_id = item['segment_id']
        new_id = counter

        wkt = LineString(item['coordinates']).wkt
        try:
            cur.execute(make_links.format(out_name=out_name, link_id=link_id,segment_id=segment_id, new_id = new_id, line=wkt, srid=srid))
            conn.commit()
            counter += 1
        except psycopg2.Error as g:
            print g.pgerror
            raise g


# def write_nodes_shapefile(nodes):
#     nodes_shp_rows = []
#     for node_idx, node in nodes.items():
#         feature = {
#             'geometry': {
#                 'type': 'Point',
#                 'coordinates': node['coordinates']
#             },
#             'type': 'Feature',
#             'properties': {
#                 'node_idx': node_idx
#             }
#         }
#         nodes_shp_rows.append(feature)
#
#     shp_schema = {
#         'geometry': 'Point',
#         'properties': {
#             'node_idx': 'int'
#         }
#     }
#     with fiona.open(RESULTS_NODES_SHP_FN, 'w',
#                     crs=from_epsg(INPUT_SHP_SRID),
#                     driver='ESRI Shapefile',
#                     schema=shp_schema) as nodes_f:
#         for row in nodes_shp_rows:
#             nodes_f.write(row)
#
#
# def write_unique_segments_shapefile(unique_segments):
#     # write shapefile segments
#     segment_shp_rows = []
#     for segment in unique_segments:
#         feature = {
#             'geometry': {
#                 'type': 'LineString',
#                 'coordinates': segment['coordinates']
#             },
#             'type': 'Feature',
#             'properties': {
#                 'link_id': segment['link_id'],
#                 'segment_id': segment['segment_id']
#             }
#         }
#         segment_shp_rows.append(feature)
#
#
#     shp_schema = {
#         'geometry': 'LineString',
#         'properties': {
#             'link_id': 'int',
#             'segment_id': 'str'
#         }
#     }
#     with fiona.open(RESULTS_SEGMENTS_SHP_FN, 'w',
#                     crs=from_epsg(INPUT_SHP_SRID),
#                     driver='ESRI Shapefile',
#                     schema=shp_schema) as segments_f:
#         for row in segment_shp_rows:
#             segments_f.write(row)


def kf_network_repair(out_name, db_conn, db_cur,srid):
    out_name = out_name
    cur = db_cur
    conn = db_conn
    print('Dropping existing tables...')
    drop_tables(cur,conn)

    # print('Load .shp GTFS links to PostGIS table...')
    # load_shp_links_to_postgis()

    print('Create endpoints PostGIS table from links...')
    load_endpoints_to_postgis(cur,conn)

    print('Create indexes on input geospatial data...')
    create_input_data_indexes(cur,conn)

    # Performing this before merging nodes should give us every
    # opportunity to find nearby relevant links since the search area
    # will be largest
    print('Find links within buffer (0.3m) of every link endpoint...')
    find_endpoint_intersections_with_links(cur,conn)

    print('Fetch the collapsed node graph (1m) with aggregated link ids...')
    nodes = fetch_collapsed_nodes(cur,conn)

    print('Reconstruct links from each associated node...')
    links = generate_links_from_collapsed_nodes(nodes,cur,conn)

    print('Cut links into segments with only 2 nodes each...')
    segments = cut_links_into_segments(nodes, links,cur,conn)

    print('Remove segments with duplicate start and end nodes...')
    unique_segments = remove_duplicate_segments(segments,cur,conn)

    print('writing unique_segments to postgres table...')
    write_unique_segments_to_postgres(out_name, unique_segments, srid,cur,conn)

    # print('Write nodes data to shapefile...')
    # write_nodes_shapefile(nodes)
    # print('Write unique segments data to shapefile...')
    # write_unique_segments_shapefile(unique_segments)

    # cur.close()
    # conn.close()
    print('Finished Processing')


# kf_network_repair(out_name, db_conn,db_cur,srid)