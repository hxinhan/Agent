#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""

Common functions

"""
import ConfigParser
import ast
import re
import json

config = ConfigParser.ConfigParser()
config.read('agent.conf')
SITES = ast.literal_eval(config.get('Clouds','sites'))

DATABASE_NAME = config.get('Database', 'DATABASE_NAME')
DATABASE_USERNAME = config.get('Database', 'DATABASE_USERNAME')
DATABASE_PASSWORD = config.get('Database', 'DATABASE_PASSWORD')
AGENT_DB_ENGINE_CONNECTION = 'mysql+mysqldb://%s:%s@localhost/%s' % (DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME)

TEMP_IMAGE_PATH = config.get('Glance', 'temp_image_path')

# A function to send resonse to end-user if resource info dose exist in agent local DB
def non_exist_response(status_code, response_body):
    
    headers = {'Content-Type': 'application/json'} 
    headers = ast.literal_eval(str(headers)).items()

    if type(response_body) == str:
        return status_code, headers, response_body
    elif type(response_body) == dict:
        return status_code, headers, json.dumps(response_body)


# A function to add cloud name and cloud ip to user response
def add_cloud_info_to_response(search_context, response):

    # Get cloud site information by using regualr expression	
    site_pattern = re.compile(r'(?<=http://).*')
    match = site_pattern.search(search_context)
    # IP address of cloud
    site_ip = match.group()
    # Find name of cloud
    site = SITES.keys()[SITES.values().index('http://'+site_ip)]

    # Add site information to json response
    try:
        response['site'] = response['site'] + ', ' +site + '-' + site_ip
    except:
        response['site'] = site + '-' + site_ip	

    return response

# Remove duplication information of response
def remove_duplicate_info(items, keyword):

    ids = []
    rs = []
    for item in items:
        if item not in rs and item[keyword] not in ids:
            ids.append(item[keyword])
            rs.append(item)
        else:
            for item2 in rs:
                if item[keyword] == item2[keyword]:
                    item2['site'] = item2['site'] + ', ' + item['site']
    return rs


def select_site_to_create_object():
    cloud_name = 'Cloud3'
    cloud_address = 'http://10.0.1.12'

    return cloud_name, cloud_address


# Read image binary data by chunks
def readInChunks(fileObj, chunkSize = 2048):
    while True:
        data = fileObj.read(chunkSize)
        if not data:
            break
        yield data



