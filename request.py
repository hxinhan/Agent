#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2016 Xin Han <hxinhan@gmail.com>
#

import ConfigParser
from nova.thread import ThreadWithReturnValue
import ast
import requests
import json
import re

config = ConfigParser.ConfigParser()
config.read('agent.conf')
SITES = ast.literal_eval(config.get('Clouds','sites'))
print SITES

# POST request t cloud
def POST_request_to_cloud(url, headers, PostData):
    res = requests.post(url, headers = headers, data = PostData)
    return res

# GET request to cloud
def GET_request_to_cloud(url, headers):
    res = requests.get(url, headers = headers)
    return res.text

# DELETE request to cloud
def DELETE_request_to_cloud(url, headers):
    res = requests.delete(url, headers = headers)
    res.headers['Content-Length'] = str(len(str(res)))
    dic = {'status_code':res.status_code, 'headers':str(res.headers), 'text':res.text}
    json_data = json.dumps(dic)
    return json_data

# A function to generate threads for boardcasting user request to clouds
def generate_threads(X_AUTH_TOKEN, url_suffix, target):

    # Create urls of clouds
    urls = []
    for site in SITES.values():
        url = site + ':' + url_suffix
        urls.append(url)
    
    # Create request header
    headers = {'X-Auth-Token': X_AUTH_TOKEN}

    # Create threads
    threads = [None] * len(urls)
    for i in range(len(threads)):
            threads[i] = ThreadWithReturnValue(target = target, args = (urls[i], headers,))
    
    return threads
