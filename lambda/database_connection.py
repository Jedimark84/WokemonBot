import os

# ARNs can be found at the following: https://github.com/keithrozario/Klayers/blob/master/deployments/python3.8/arns/eu-west-2.csv
# Import pymysql 0.10.0 from layer: arn:aws:lambda:eu-west-2:770693421928:layer:Klayers-python38-PyMySQL:2
# Is this a trusted source? Maybe we should create our own pymysql layer to use. Or bundle with lambda function.
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
                                 cursorclass=pymysql.cursors.DictCursor,
                                 init_command="SET SESSION time_zone='Europe/London';")
    return connection
