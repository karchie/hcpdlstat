# Copyright (c) 2013 Washington University School of Medicine
# Author: Kevin A. Archie <karchie@wustl.edu>

import ConfigParser
import json, os, pymysql, urllib2

columns = {'ip':'varchar(16) not null',
           'country_code':'varchar(2)',
           'country_name':'varchar(256)',
           'region_code':'varchar(64)',
           'region_name':'varchar(256)',
           'city':'varchar(256)',
           'zipcode':'varchar(64)',
           'latitude':'double',
           'longitude':'double',
           'metro_code':'varchar(64)',
           'areacode':'varchar(64)',
           'source':'varchar(256)',
           'created':'datetime',
       }


def create_geo_table(db):
    cur = db.cursor()
    try:
        cur.execute('create table if not exists geolocation.geo ('
                    + ','.join(('{0} {1}'.format(n,t) for n,t in columns.items()))
                    + ', primary key (`ip`) )')
    finally:
        cur.close()

def get_geo(ip):
    response = urllib2.urlopen('http://freegeoip.net/json/{0}'.format(ip))
    geo = json.load(response)
    geo['source']='http://freegeoip.net'
    return geo
    
def column_value(k, entry):
    if 'created' == k:
        return 'now()'
    else:
        v = entry[k]
        return u"'{0}'".format(str(v).replace("'","''")) if v else 'NULL'

def insert_geo(db, geo):
    cur = db.cursor()
    try:
        cur.execute(u'insert into geolocation.geo ('
                    + u','.join(columns.keys())
                    + u') values ('
                    + u','.join([column_value(k, geo) for k in columns.keys()])
                    + u')')
    except UnicodeEncodeError as e:
        print 'skipping', geo['ip'], '-', geo, ':', e
    except pymysql.err.ProgrammingError as e:
        print 'skipping', geo['ip'], '-', geo, ':', e
    finally:
        cur.close()

def get_missing_geo(db):
    cur = db.cursor()
    try:
        cur.execute('select distinct s.client_addr from aspera_stats_collector.fasp_sessions as s '
                    + 'left join geolocation.geo as g on s.client_addr = g.ip '
                    + 'where g.ip is null')
        for r in cur.fetchall():
            if r[0]:
                geo = get_geo(r[0])
                insert_geo(db, geo)
    finally:
        cur.close()

def main():
    config = ConfigParser.ConfigParser()
    config.read(['site.cfg', os.path.expanduser('~/.hcpdlstat.cfg')])
    get_config = lambda k: config.get('statscollector',k)

    host = get_config('mysql.host')
    port = int(get_config('mysql.port'))
    user = get_config('mysql.user')
    passwd = get_config('mysql.password')

    db = pymysql.connect(host=host,port=port,user=user,passwd=passwd)
    try:
        create_geo_table(db)
        get_missing_geo(db)
    finally:
        db.close()
