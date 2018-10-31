# GTFS-to-Roads-converter
This collection of scripts builds a database from GTFS files and then converts the route shapes into a simplified stand-in road network consisting of clean center lines and consistent topology. By default, the script accepts a database table as input, chops it up, simplifies it, and returns a databse table as output. While the code required to process shapefiles as input/out is present in the scripts, it has not been refined or sufficiently tested as of yet. 

Python 2.7 - PostgreSQL 9.6 - PostGIS 2.4.0 - GEOS 3.6.2
Input parameters and filenames are outlined under the master control script's description
Here is a short description of each script:

- Convert_gtfs_to_roadlinks_master.py: This is the master control script which excutes the others and where the user enters all the parameters specific to their transit agency / city.
  USER INPUTS: import type_def_CITYNAME as type_def  = user must edit this line (line 9) to reflect type_def name of current agency
               cityname = name of the city or transit agency to become database name
               SRID = the spatial reference identifier for the original data / the study region
               Datum = the datum of the original coordinates (most often 4326 = WGS84)
               to_be_chopped = the name of the database table which will be chopped up and simplified by the script
               out_name = the name of the resultant output database table which contains the simplified network
               gtfs_filepath = the filepath to the UNZIPPED gtfs files <<<PENDING UPDATE
               gtfs_shapefile_input = <<<PENDING UPDATE>>the filepath to the shapefile being used as input (instead of referencing
               a databse table)
               roadlinks_output = <<<PENDING UPDATE>>the filepath (ending in filename) of the resultant output shapefile (if the
               user choses to export a .shp instead of a table)

- make_db.py: scans the GTFS directory to obtain filenames and then creates a postgres database with one table per .txt file
  USER INPUTS: If running in isolation - user must specify the GTFS filepath as well as a name for the database (typically city or agency name)

- type_def_CITYNAME.py: this is a dfinition file which provides data types for each column created by the make_db script.
  USER INPUTS: the type_def file must be edited and renamed for each new GTFS feed. For example, a route_id may be of type integer for most agencies, but require character varying(xx) for another. Not all GTFS feeds have all the same columns and the type_def file will have to be edited to reflect this. 

- setup_db.py: This script adds the PostGIS extension to the database, and then constructs LineStrings from the shapes.txt file to represent bus routes and creats Point features from stops locations
  USER INPUTS: if run in isolation - user must provide SRID and datum 

-GTFS_network_simplifier: this script executes mutiple SQL queries in the database in order to "chop up" the route linestrings into their component line segments. (you could say it "decomposes" the network into its most basic component line segments) these segments are then processed to eliminate duplicates and near-duplicates.

- flatten_network: This script executes a ST_DBScan process on the output of the GTFS_network_simplifier script in order to address the final, most problematic, class of erroneous linstring. It assigns all termination nodes an identifier according to which line-Strings are st_dwithin a certain distance of each node. This helps identify which linestrings are close to more than 2 termination nodes. a new list of linestrings is constructed from the strings which only have two associated nodes, or the linestrings which have been chopped in the case where a linestring was close to more than 2 termination nodes. 
  USER INPUT: here the user must specify the distance the DBScan will examine around each linestring looking for nodes. by default it is set at 0.4 map units (meters in the case of SRID 32618). Too small of a value may result in erroneuous linestrings NOT being corrected, too large of a value and some lineStrings which do not actually conflict may be removed from the record. the user must inspect output layers in a GIS software to ensure a correct value has been used.
