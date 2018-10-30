#### GTFS NETWORK SIMPLIFIER ###
# This script turns a GTFS network into a simplified representation with consistent topology rules
# The resulting layer can be used as a stand in "base layer" in place of a street network
# March 23 2018 - TRIP LAB CONCORDIA UNIVERSITY MONTREAL
# Author: Marshall Davey

import psycopg2
# from shapely import LineString
from shapely.geometry import LineString
#### SETUP SOME VARIABLES ####
# name of the database table to be chopped up
# to_be_chopped = 'routs_id'
##SET the SRID OF THE OUTPUT 326+'UTM zone" for Canada. Montreal = 16
# srid = 32618
#  SET THE FOLLOWING IF YOU ARE HANDLING SHAPEFILES INSTEAD OF DATABASE TABLES
# INPUT_SHP_FN = "D:\mtl_roads_ests\dist_links_new.shp"
# INPUT_SHP_SRID = 32618
# RESULTS_NODES_SHP_FN = 'D:\mtl_roads_ests/nodes_kf30new.shp'
# RESULTS_SEGMENTS_SHP_FN = 'D:\mtl_roads_ests/unique_segments_kf30new.shp'


# global db_cur
# global db_conn
# try:
#     db_conn = psycopg2.connect(user='postgres', host='localhost', password='postgres', port=5432,
#                                database='montreal_test')
#     db_cur = db_conn.cursor()
#     print "successfully connected to %s" % ('montreal_test')
# except:
#     print "cannot connect"

# def load_shp_links_to_postgis(db_cur,db_conn):
#     cur = db_cur
#     conn = db_conn
#
#     # the table columns bellow must be edited to match the shapefile
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


def chopper(to_be_chopped,srid, db_conn, db_cur):
    make_links_table = """
        DROP TABLE IF EXISTS routs_id_links;
        CREATE TABLE routs_id_links (link_id integer, link_geom geometry);"""

    read_linemerge_feature = """
             SELECT
             json_build_object(
                 'type', 'Feature',
                 'geometry', ST_AsGeoJSON(st_linemerge(ST_collect(geom)))::json,
                                                 'properties', json_build_object(
                'type', 'type'
             )
             )
             FROM
             {to_be_chopped};
             """

    db_cur.execute(make_links_table)
    db_cur.execute(read_linemerge_feature.format(to_be_chopped=to_be_chopped))
    u_names = db_cur.fetchone()
    geo_dict = u_names[0]
    lines_from_json = []
    for item in geo_dict['geometry']['coordinates']:
        lines_from_json.append(item)
    print 'len of lines_from_json is %s' % len(lines_from_json)
    new_lines = []
    for feature in lines_from_json:
        last_point = None
        for coordinate in feature:
            if last_point:
                new_lines.append((last_point, coordinate))
            last_point = coordinate

    make_links = """
        INSERT INTO routs_id_links (link_id, link_geom)
        VALUES ( {link_id}, (ST_GeomFromText(('{line}'), {srid})) ) ;
        """

    print "number of lines in new_lines to create %s" % len(new_lines)
    # print "writing table %s" % road_file_name
    counter = 0
    for item in new_lines:
        link_id = counter
        wkt = LineString(item).wkt
        try:
            db_cur.execute(make_links.format(link_id=link_id, line=wkt, srid=srid))
            db_conn.commit()
            counter += 1
        except psycopg2.Error as g:
            print g.pgerror
            raise g

    remove_dup_links = """
    DROP TABLE IF EXISTS distinct_links;
    SELECT DISTINCT ON (link_geom) link_geom, link_id as link_id into distinct_links from routs_id_links;
    CREATE INDEX dis_links_gix on distinct_links USING GIST (link_geom);
    """
    db_cur.execute(remove_dup_links)
    db_conn.commit()

    try:
        remove_similar_links = """
         DROP TABLE IF EXISTS distinct_buffs;
         SELECT st_buffer(st_centroid(link_geom), 0.25) AS buff_geom, link_id AS link_id INTO distinct_buffs FROM distinct_links;
         CREATE INDEX dis_buffs_gix ON distinct_buffs USING GIST (buff_geom);

         DROP TABLE IF EXISTS distinct_links_duplicate;
          SELECT * into distinct_links_duplicate from distinct_links;

         DELETE from distinct_buffs dt
         WHERE EXISTS (
         SELECT *
         FROM distinct_buffs ex
         WHERE st_intersects(ex.buff_geom,dt.buff_geom)
         AND ex.link_id < dt.link_id
         );

         DELETE from distinct_links dt
         WHERE link_id NOT IN (
         SELECT link_id
         FROM distinct_buffs);
         """
        db_cur.execute(remove_similar_links)
        db_conn.commit()
    except psycopg2.Error as e:
        print e.pgerror
        raise e

    # flatten_network.kf_network_repair('routs_id_flat_test4', db_conn, db_cur, srid)

# chopper(to_be_chopped,srid,db_conn,db_cur)