###--- GTFS TO ROADLINKS CONVERTER - MASTER CONTROL FILE ---###
## October 2018 - MARSHALL DAVEY - Montreal, Canada
## This script executes the other scripts in the respository in order to carry out the following
#  1) create a GTFS database in postgres
#  2) convert the shapes and stops.txt files into geometry layers in the db
#  3) Chop up the GTFS route shapes and create a new network layer with a simplified
#     topology which replaces the need for a street network layer in GIS analysis.
import psycopg2, os, time, sys
from scripts import type_def_STM_2017 as type_def
from scripts import GTFS_network_simplifier, setup_db, make_db, flatten_network
start = time.time()

# set some variables
cityname = 'mtl_solo_test'  #this sets the databse name
srid = 32618       #set the spatial reference ID   EPSG 326+ UTM Zone Van = 10, toronto = 17, Montreal = 18
datum = 4326       # DATUM of the SRID and original data  4326 = WGS84
to_be_chopped = 'routs_id'
out_name = 'gtfs_as_roadlinks'

#set filepaths and names
directory = os.path.dirname(sys.argv[0])
gtfs_filepath = "D:\Arol_thesis\gtfs\stm"
# gtfs_shapefile_input =
# roadlinks_output =

def create_gtfs_database(cityname,gtfs_filepath,type_def):
    try:
        make_db.make_db(cityname, gtfs_filepath, type_def)
    except psycopg2.Error as e:
        print e.pgcode
        print e.pgerror

def create_routes(cityname,srid,datum, db_conn,db_cur):
    try:
        setup_db.setup_db(cityname, srid, datum, db_conn, db_cur)
    except psycopg2.Error as e:
        print e.pgcode
        print e.pgerror

def merge_and_chop_routes(to_be_chopped, srid, db_conn, db_cur):
    try:
        GTFS_network_simplifier.chopper(to_be_chopped, srid, db_conn, db_cur)
    except psycopg2.Error as e:
        print e.pgcode
        print e.pgerror
        print 'An error interrupted the network simplifying process =('

def flatten_links(out_name, db_conn, db_cur, srid):
    try:
        flatten_network.kf_network_repair(out_name, db_conn, db_cur, srid)
    except psycopg2.Error as e:
        print e.pgcode
        print e.pgerror
        print 'An error interrupted the link flattening process :( '


def master_process(cityname,gtfs_filepath,srid, datum, to_be_chopped, out_name):
    print 'generating gtfs database: %s in Postgres' % (cityname)
    create_gtfs_database(cityname,gtfs_filepath, type_def)

    global db_cur
    global db_conn
    try:
        db_conn = psycopg2.connect(user='postgres', host='localhost', password='postgres', port=5432, database=cityname)
        db_cur = db_conn.cursor()
    except:
        print "cannot connect"
        raise

    print 'generating requisite routes and shapes tables in postgres'
    create_routes(cityname,srid,datum, db_conn ,db_cur)

    print 'merging and chopping up routes into new road-links on faile/table: %s' % (to_be_chopped)
    merge_and_chop_routes(to_be_chopped, srid, db_conn, db_cur)

    print "removing near_duplicate links from %s and exporting %s " % (to_be_chopped, out_name)
    flatten_links(out_name, db_conn, db_cur, srid)


    print "total elapsed time: %s hours" % (((time.time() - start) / 60) / 60)

master_process(cityname,gtfs_filepath, srid, datum, to_be_chopped, out_name)