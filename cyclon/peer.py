#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""

CYCLON Protocol Peer Class

"""

from threading import Thread
import time
from time import gmtime, strftime
from common import *
from db import *
from models import *
from request import *

import memcache
mc = memcache.Client([MEMCACHED_SERVER_IP], debug=1)

# Get introducer's ip address (CYCLON Protocol)
INTRODUCER_IP = 'http://' + config.get('CYCLON', 'introducer_ip') 
AGENT_IP = 'http://' + get_lan_ip() + ':' + config.get('Agent', 'listen_port')
NEIGHBORS = []

# Neighbor object
class Neighbor(object):

    def __init__(self, ip_address, age):
        self.ip_address = ip_address
        self.age = int(age)
    
    def __str__(self):
        return "ip_address: %s, age: %s" % (self.ip_address, self.age)

class Peer(Thread):
     
    def __init__(self, interval, neighbors):
        Thread.__init__(self)
        self.isJoined = False
        self.STOP = False
        self.interval = interval
        self.neighbors = neighbors
        #self.lock = lock
        
        if INTRODUCER_IP != AGENT_IP:
            introducer = Neighbor(INTRODUCER_IP, 0)
            self.neighbors.append(introducer)
            # Save neighbor list to memcached (expiration up to 30 days)
            mc.set("neighbors", self.neighbors, 0)
        else:
            mc.set("neighbors", [], 0)
    
    #def __str__(self):
    #    return "neighbors: %" % (self.neighbors)

    def run(self):

        if not self.isJoined:
            print 'Peer needs to join the P2P network first...'
            print 'Introducer IP Address: %s' % INTRODUCER_IP 
            print 'Agent IP Address: %s' % AGENT_IP

            if INTRODUCER_IP != AGENT_IP:
                print 'Introducer is another agent...'
                self.peer_join(INTRODUCER_IP, AGENT_IP)
            else:
                print 'Introducer is agent itself...'
                #mc.set("neighbors", [], 0)
                self.isJoined = True
                #self.peer_join(INTRODUCER_IP, agent_ip)

        #for i in range(3):
        while not self.STOP and self.isJoined:
            time.sleep(self.interval)
            print 'CYCLON protocol runs every %d seconds, %s' % (self.interval, strftime("%Y-%m-%d %H:%M:%S", gmtime())) 
            
            # Update all neighbors' age by one
            self.update_age()
            #self.lock.acquire()
            #print 'CYCLON Thread Lock Acquire...'
	    self.view_exchange()
            #self.lock.release()
            #print 'CYCLON Thread Lock Release...'
    

    # New peer sends a request to its introducer to join the P2P network
    def peer_join(self, introducer_ip, agent_ip):
        print 'Peer is joining the P2P network...'
        
        headers = {'Content-Type':'application/json; charset=UTF-8'}
        url = introducer_ip + '/v1/agent/cyclon/new_peer_join'
        dic = {"new_peer" : {"ip_address" : agent_ip} }
        
        res = POST_request_to_cloud(url, headers, json.dumps(dic))

	# If introducer's length of neighbors list is less than FIXED_CACHE_SIZE
	if res.status_code == 201:
	    print 'Waiting for responses from introducer\'s neighbors...'
        elif res.status_code == 202:
	    print 'Waiting for random walk endpoint\' response...'

        # New peer generates several threads to initiat a shuffle of lenght 1 with nonadjacent nodes received from its introducer
        self.isJoined = True
    

    # Update peer's all neighbors' age by one
    def update_age(self):

        self.neighbors = mc.get("neighbors")

        if len(self.neighbors) == 0:
            pass
        else:
            print '-'*50
            print 'FIXED_SIZE_CACHE: %s' % FIXED_SIZE_CACHE
            print 'SHUFFLE_LENGTH: %s' % SHUFFLE_LENGTH
            print 'len of neighbors list: %d' % len(self.neighbors)
            for i in range(len(self.neighbors)):
                # Update neighbor's age by one                
                self.neighbors[i].age = self.neighbors[i].age + 1
                print "age: %s" % self.neighbors[i].age
                print "ip_address: %s" % self.neighbors[i].ip_address
                # Save neighbor list to memcached (expiration up to 30 days)
                mc.set("neighbors", self.neighbors, 0)
            print '-'*50

    # Peer exchanges it view of neighbors with one of its oldest neighbor
    def view_exchange(self):
	
	print 'Peer View Exchange...'

	self.neighbors = mc.get("neighbors")
	
	if len(self.neighbors) == 0:
            print 'No neighbor exists, waiting for neighbor to join...'
	    pass
    	else:
            # Pick up a oldest neighbor from neighbors list
	    oldest_neighbor = self.pick_neighbor_with_highest_age(self.neighbors)
            # Create a subset containing SHUFFLE_LENGTH neighbors
            subset = self.select_subnet_randomly(self.neighbors, oldest_neighbor)

	    print '!'*80
            print 'Oldest Neighbor IP Address: %s' % oldest_neighbor.ip_address
            print 'Oldest Neighbor Age: %s' % oldest_neighbor.age
            print 'Subset Length: %d' % len(subset)
            for item in subset:
                print item.ip_address
                print item.age
	    print '!'*80
            # Send selected subset to the oldest neighbor
            self.send_to_oldest_neighbor(oldest_neighbor, subset)


    # Pick up the oldest neighbor from neighbors list
    def pick_neighbor_with_highest_age(self, neighbors):
        print 'Pick up oldest neighbor...'

	oldest_neighbor = neighbors[0]
        oldest_neighbors = []
	for neighbor in neighbors:
	    if neighbor.age >= oldest_neighbor.age:
	        oldest_neighbor = neighbor
                oldest_neighbors.append(oldest_neighbor)
	
	return random.choice(oldest_neighbors)
	

    # Select SHUFFLE_LENGTH - 1 random neighbors
    def select_subnet_randomly(self, neighbors, oldest_neighbor):
        print 'Select Subnet Randomly...'

        print '*'*100
        temp_list = []
        for neighbor in neighbors:
            if neighbor != oldest_neighbor:
                temp_list.append(neighbor)

        subset = []
        if len(temp_list) != 0:
            for i in range(SHUFFLE_LENGTH-1):
                subset.append(random.choice(temp_list))
    
        # Replace oldest neighbor's entry with a new entry of age 0 and with agent's ip address
        #agent_ip = 'http://' + get_lan_ip() + ':' + config.get('Agent', 'listen_port')
        subset.append(Neighbor(AGENT_IP, 0))

        return subset

    '''
    # Update agent's neighbor list
    def update_neighbor_list(self, oldest_neighbor, subset):
        neighbors = mc.get("neighbors")
        new_neighbors = []
        for neighbor in neighbors:
            #if neighbor not in subset and neighbor is not oldest_neighbor:
            if neighbor.ip_address != oldest_neighbor.ip_address:
            #if neighbor != oldest_neighbor:
                new_neighbors.append(neighbor)
        #mc.set("neighbors", new_neighbors, 0)
    '''

    def send_to_oldest_neighbor(self, oldest_neighbor, subset):
        print 'Send to oldest neighbor...'
        
        headers = {'Content-Type': 'application/json'}
        url = oldest_neighbor.ip_address + '/v1/agent/cyclon/receive_view_exchange_request'
        neighbors = []
        for neighbor in subset:
            #dic = {"neighbor":{"ip_address":neighbor.ip_address, "age":neighbor.age}}
            dic = {"ip_address":neighbor.ip_address, "age":neighbor.age}
            neighbors.append(dic)

        post_data = {"neighbors":neighbors}
        print post_data
        print '-'*50
        print json.dumps(post_data)
        res = POST_request_to_cloud(url, headers, json.dumps(post_data))
        





