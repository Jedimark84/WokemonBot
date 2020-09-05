import os
import pymysql.cursors

DB_ENDPOINT = os.environ['DB_ENDPOINT']
DB_USERNAME = os.environ['DB_USERNAME']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_SCHEMA   = os.environ['DB_SCHEMA']

def connect():
    # Connect to the database
    connection = pymysql.connect(host=DB_ENDPOINT,
                                 user=DB_USERNAME,
                                 password=DB_PASSWORD,
                                 db=DB_SCHEMA,
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)
    return connection
