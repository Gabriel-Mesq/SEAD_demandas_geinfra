from flask import Flask
import pymysql

app = Flask(__name__)

def get_db_connection():
    return pymysql.connect(user='root', password='melhor1@', host='127.0.0.1', database='demandas_geinfra_dev')
