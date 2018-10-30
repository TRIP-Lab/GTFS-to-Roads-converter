def setup_db(cityname, SRID, DATUM, db_conn, db_cur):
    # Create the postgis extension, turn shapes.txt into a LineString routes table.
    try:
        query = """
        CREATE EXTENSION postgis;
        ALTER TABLE shapes ADD COLUMN geom geometry;
        UPDATE shapes
        SET geom = ST_Transform(ST_SetSRID(ST_MakePoint(shape_pt_lon,shape_pt_lat),{datum}), {srid});
        --SET geom = ST_SetSRID(ST_MakePoint(shape_pt_lon,shape_pt_lat),{datum});

        VALUES ('{datum}', '{srid}')
        """
        db_cur.execute(query.format(datum=DATUM, srid=SRID))
        db_conn.commit()
        print 'updating shapes'
    except psycopg2.Error as f:
        print 'failed to update shapes'
        print f.pgcode
        print f.pgerror
        raise f

    #  create POINT geometry for the stops table
    # OPTIONAL Update the stops table to create POINT features at stop locations
    try:
        stops_query = """
        ALTER TABLE stops ADD column geom geometry;
        UPDATE stops SET geom = ST_Transform(ST_SetSRID(ST_MakePoint(stop_lon, stop_lat),{datum}), {srid});
         VALUES ('{datum}', '{srid}')
         """
        db_cur.execute(stops_query.format(datum=DATUM, srid=SRID))
        print 'updating stops'
    except psycopg2.Error as e:
        print 'failed to update stops'
        print e.pgcode
        print e.pgerror
        raise e
    db_conn.commit()
    ## Create LineStrings from the POINT features in shapes.txt ***"routs" spelling is intentional***
    try:
        db_cur.execute("""
        drop table if exists routs_id;
        with routs as(
	            SELECT points.shape_id,
	            ST_MakeLine(points.geom ORDER BY points.shape_pt_sequence ASC) As geom                
		            FROM shapes As points
		            GROUP BY points.shape_id
		             )
        select r.*
        into routs_id
        from routs r;""")
        db_conn.commit()
        print 'writing routs_id table'
    except psycopg2.Error as h:
        print 'failed to write routs_id'
        print h.pgcode
        print h.pgerror
        raise h


    # # make a bus routes table to be used throughout the rest of the script
    # make_buss = """
    # DROP TABLE IF EXISTS bus_routes;
    # SELECT rt.shape_id as shape_id, rt.geom as geom into bus_routes from routs_id rt, trips trip, routes rout
    # WHERE rt.shape_id = trip.shape_id and trip.route_id = rout.route_id AND rout.route_type = 3
    # GROUP BY rt.shape_id, rt.geom;
    # """
    #
    # try:
    #     print "making bus_routes table"
    #     db_cur.execute(make_buss)
    #     db_conn.commit()
    # except psycopg2.Error as e:
    #     print "failed to print bus routes table"
    #     print e.pgerror
    #     print e.pgcode
    #     raise e
