import sqlalchemy

type_dict = {
    'agency': [
        ('agency_id', 'text'),
        ('agency_name', 'text'),
        ('agency_url', 'text'), 
        ('agency_timezone', 'text'), 
        ('agency_lang', 'text'),
        ('agency_phone', 'text'), 
        ('agency_fare_url', 'text'),
    ],
 
     'calendar_dates' : [
        ('service_id', 'character varying(50)'),
        ('date', 'integer'),
        ('exception_type', 'integer'),
    ],
    'fare_attributes': [
        ('fare_id', 'text'),
        ('price', 'real'),
        ('currency_type', 'text'),         
        ('payment_method', 'text'),
        ('transfers', 'text'),
        ('transfer_duration', 'integer'),       
    ],

    'fare_rules': [
        ('fare_id', 'text'), 
        ('route_id', 'integer'),
        ('origin_id', 'text'),
        ('destination_id', 'text'),
        ('contains_id', 'text'),      
   ],


    'feed_info': [
        ('feed_publisher_name', 'text'), 
        ('feed_publisher_url', 'text'),
        ('feed_lang', 'text'),
        ('feed_start_date', 'integer'),
        ('feed_end_date', 'integer')
    ],

    'frequencies': [
        ('trip_id', 'character varying(50)'),
        ('start_time', 'interval'),
        ('end_time', 'interval'),
        ('headway_secs', 'integer')
    ],
    
    'routes': [
        ('route_id', 'integer'),
        ('agency_id', 'text'),
        ('route_short_name', 'text'),
        ('route_long_name', 'text'),
        ('route_type', 'integer'),
        ('route_url', 'text'),
        ('route_color', 'text'),
        ('route_text_color', 'text')
    ],

    'shapes': [
        ('shape_id', 'character varying(50)'),
        ('shape_pt_lat', 'real'),
        ('shape_pt_lon', 'real'),
        ('shape_pt_sequence', 'integer'),
    ],

    'stop_times': [
        ('trip_id', 'character varying(50)'),
        ('arrival_time', 'interval'),
        ('departure_time', 'interval'),
        ('stop_id', 'character varying(50)'),
        ('stop_sequence', 'integer'),
        
    ],
    'stops': [
        ('stop_id', 'character varying(50)'),
        ('stop_code', 'text'),
        ('stop_name', 'text'),
        ('stop_lat', 'real'), 
        ('stop_lon', 'real'),
        ('stop_url', 'text'),
        ('location_type', 'integer'),
        ('parent_station', 'character varying(10)'),
        ('wheelchair_boarding', 'integer')
    ],
    'trips': [
        ('route_id', 'integer'),
        ('service_id', 'character varying(50)'),
        ('trip_id', 'character varying(50)'),
        ('trip_headsign', 'text'),
        ('direction_id', 'integer'),
        ('shape_id', 'character varying(50)'),
        ('wheelchair_accessible', 'text'),
        ('note_fr', 'text'),
        ('note_en2', 'text')
    ]
}
