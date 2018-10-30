import psycopg2, os

def make_db(cityname, gtfs_files,type_def):
    # authored by Kyle Fitzsimmons, edited by Marshall Davey
    # This script will create a postgres database from a GTFS collection
    # This script MUST be accompanied by a "type_def" script which specifies column headers/data types

    # begin by gathering all gtfs .txt files in given directory
    gtfs_data_dir = gtfs_files
    files = []
    for root, directory, filename in os.walk(gtfs_data_dir):
        for f in filename:
            if f.endswith('.txt'):
                # (table name from filepath, filepath)
                files.append((f.split('.')[0], os.path.join(root, f)))

    # create the database
    print("Creating new gtfs database...")
    create_conn = psycopg2.connect(user='postgres',password ='postgres', host='localhost', port=5432)
    create_cur = create_conn.cursor()
    create_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    drop = """DROP DATABASE IF EXISTS {};"""
    create_cur.execute(drop.format(cityname))
    name = """CREATE DATABASE {};"""
    create_cur.execute(name.format(cityname))
    create_cur.close()
    create_conn.close()

    # connect to the new database
    global db_cur
    global db_conn
    try:
        db_conn = psycopg2.connect(user='postgres', host='localhost',password ='postgres', port=5432, database=cityname)
        db_cur = db_conn.cursor()
    except:
        print "cannot connect"
        raise

    # create table using schema file
    table_defs = type_def.type_dict
    for table, col_defs in table_defs.iteritems():

        print('Creating table {}'.format(table))
        create_table_sql = """CREATE TABLE {}(""".format(table)
        for idx, col_def in enumerate(col_defs):
            create_table_sql += """{} {}""".format(*col_def)
            if idx + 1 != len(col_defs):
                create_table_sql += ', '
        create_table_sql += """);"""
        db_cur.execute(create_table_sql)
    db_conn.commit()

    # add gtfs .txt files to database
    copy_sql = """
        COPY {} FROM STDIN WITH
            CSV
            HEADER
            DELIMITER AS ','
        """
    for file_tuple in files:
        table_name, file_path = file_tuple
        if table_name == "agency": continue
        print('Adding {}'.format(table_name))

        db_rows = []
        with open(file_path, 'r') as gtfs_data:
            db_conn.cursor().copy_expert(sql=copy_sql.format(table_name), file=gtfs_data)
    db_conn.commit()

    # tables (keys) to create indices on in db (values)
    index_dict = {
        'calendar_dates': ['date'],
        'routes': ['route_type'],
        'trips': ['route_id', 'trip_id'],
        'stop_times': ['trip_id', 'arrival_time'],
        'stops': ['stop_id']
    }

    for table, indices in index_dict.iteritems():
        print('Creating index on {}'.format(table))
        index_sql = """CREATE INDEX {}_idx ON {} (""".format(table, table)
        index_sql += (', ').join(indices)
        index_sql += """);"""
        print index_sql
        db_cur.execute(index_sql)
    db_conn.commit()

    # create view for specific python query (rework this)
    print('Create (temporary) view')
    db_cur.execute(
        """CREATE VIEW st_join_t AS SELECT t.trip_id, t.route_id, t.service_id, s.arrival_time FROM trips t INNER JOIN stop_times s ON t.trip_id=s.trip_id;""")
    db_conn.commit()


    return db_cur, db_conn

# make_db(cityname,gtfs_files)