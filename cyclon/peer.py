#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""

CYCLON Protocol Peer Class

"""

from threading import Thread, Lock
import time
from time import gmtime, strftime
#from common import *
from db import *
from models import *
from request import *
from cyclon.config import *
from cyclon.common import *

lock = Lock()
view_exchange_lock = Lock()

# Get introducer's ip address (CYCLON Protocol)
#INTRODUCER_IP = 'http://' + config.get('CYCLON', 'introducer_ip') + ':' + config.get('Agent', 'listen_port') 
INTRODUCER_IP = config.get('CYCLON', 'introducer_ip') 
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
        #self.neighbors = neighbors
        
        if INTRODUCER_IP != AGENT_IP:
            introducer = Neighbor(INTRODUCER_IP, 0)
            #self.neighbors.append(introducer)
            neighbors = []
            neighbors.append(introducer)
            #write_to_memory_cache("neighbors", self.neighbors)
            write_to_memory_cache("neighbors", neighbors)
        else:
            write_to_memory_cache("neighbors", [])
    
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
    	    #print 'peer.py waiting for view_exchange_lock.acquire()'
            view_exchange_lock.acquire()
    	    #print 'peer.py view_exchange_lock.acquire()'
            self.update_age()
            view_exchange_lock.release()
            
	    # Peer exchanges its view with the peer with highest age from its neighbros list
            view_exchange_lock.acquire()
	    self.view_exchange()
            view_exchange_lock.release()
    	    #print 'peer.py view_exchange_lock.release()'
    

    # New peer sends a request to its introducer to join the P2P network
    def peer_join(self, introducer_ip, agent_ip):
        #print 'Peer is joining the P2P network...'
        
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

        #self.neighbors = read_from_memory_cache("neighbors")
        neighbors = read_from_memory_cache("neighbors")

        if len(neighbors) == 0:
            pass
        else:

            if len(neighbors) > FIXED_SIZE_CACHE:
                print 'SHIT HAPPENED!!! '*500
                time.sleep(30)

            print '-'*50
            print 'FIXED_SIZE_CACHE: %s' % FIXED_SIZE_CACHE
            print 'SHUFFLE_LENGTH: %s' % SHUFFLE_LENGTH
            #print 'len of neighbors list: %d' % len(self.neighbors)
            print 'len of neighbors list: %d' % len(neighbors)
            #for i in range(len(self.neighbors)):
            for i in range(len(neighbors)):
                # Update neighbor's age by one                
                neighbors[i].age = neighbors[i].age + 1
                
		print '%s, %d' % (neighbors[i].ip_address, neighbors[i].age)

                # Save neighbor list to memcached (expiration up to 30 days)
                write_to_memory_cache("neighbors", neighbors)
            
	    print '-'*50

    # Peer exchanges it view of neighbors with one of its oldest neighbor
    def view_exchange(self):
	
	#print 'Peer View Exchange...'

	#self.neighbors = read_from_memory_cache("neighbors")
	neighbors = read_from_memory_cache("neighbors")

	if len(neighbors) == 0:
            print 'No neighbor exists, waiting for neighbor to join...'
	    pass
    	else:
            # Pick up a oldest neighbor from neighbors list
	    oldest_neighbor = self.pick_neighbor_with_highest_age(neighbors)
        
	    # Create a subset containing SHUFFLE_LENGTH neighbors
            selected_subset, sent_subset = self.select_subnet_randomly(neighbors, oldest_neighbor)

            # Send selected subset to the oldest neighbor
            self.send_to_oldest_neighbor(neighbors, oldest_neighbor, selected_subset, sent_subset)


    # Pick up the oldest neighbor from neighbors list
    def pick_neighbor_with_highest_age(self, neighbors):
        #print 'Pick up oldest neighbor...'

	oldest_neighbor = neighbors[0]
        oldest_neighbors = []
	for neighbor in neighbors:
	    if neighbor.age > oldest_neighbor.age:
	        oldest_neighbor = neighbor
        
        for neighbor in neighbors:
            if neighbor.age == oldest_neighbor.age:
                oldest_neighbors.append(oldest_neighbor)
        
	oldest_neighbor = random.choice(oldest_neighbors)
	
	# Remove the oldest neighbor from local memory cahce
        neighbors = remove_from_list(neighbors, oldest_neighbor)
        write_to_memory_cache("neighbors", neighbors)
	
	return oldest_neighbor
	

    # Select SHUFFLE_LENGTH - 1 random neighbors
    def select_subnet_randomly(self, neighbors, oldest_neighbor):
        #print 'Select Subnet Randomly...'
	
	#neighbors = read_from_memory_cache("neighbors")

        temp_list = []
        for neighbor in neighbors:
            if neighbor != oldest_neighbor:
                temp_list.append(neighbor)

        selected_subset = []
        sent_subset = []
        if len(temp_list) != 0:
            for i in range(SHUFFLE_LENGTH-1):
                selected_subset.append(random.choice(temp_list))
                sent_subset.append(random.choice(temp_list))

        # Remove redundant neighbors
        selected_subset = remove_neighbors_with_same_ip(selected_subset)
        sent_subset = remove_neighbors_with_same_ip(sent_subset)
    
        selected_subset.append(oldest_neighbor)
        # Replace oldest neighbor's entry with a new entry of age 0 and with agent's ip address
        sent_subset.append(Neighbor(AGENT_IP, 0))

        return selected_subset, sent_subset


    def send_to_oldest_neighbor(self, neighbors, oldest_neighbor, selected_subset, sent_subset):
        print 'Send to oldest neighbor -> ip_address: %s, age: %s' % (oldest_neighbor.ip_address, oldest_neighbor.age)
        
        headers = {'Content-Type': 'application/json'}
        url = oldest_neighbor.ip_address + '/v1/agent/cyclon/receive_view_exchange_request'
        
        sent_neighbors_data = []
        for neighbor in sent_subset:
            dic = {"ip_address":neighbor.ip_address, "age":neighbor.age}
            sent_neighbors_data.append(dic)
        post_data = {"neighbors":sent_neighbors_data}

	#print 'Send to the oldest neighbor'
	#print post_data
        
        try:
            #res = POST_request_to_timeout(url, headers, INTERVAL, json.dumps(post_data))
            res = POST_request_to_timeout(url, headers, 10, json.dumps(post_data))
            #res = POST_request_to_cloud(url, headers, json.dumps(post_data))
            received_neighbors = res.json()['neighbors']

	    #print 'Received from the oldest neighbor: %s' % oldest_neighbor.ip_address
	    #print received_neighbors

            # Update local neighbors list in memeory cache    
            update_neighbors_cache(received_neighbors, selected_subset)
        
        except:
            print 'Connection Timeout... '
            print 'Peer %s left from the P2P network...' % oldest_neighbor.ip_address


# Read neighbors list from memory cache
def read_from_memory_cache(key):
    lock.acquire()
    try:
        neighbors = mc.get(key)
    finally:
        lock.release()
        return neighbors

# Write neighbor list to memory cache
def write_to_memory_cache(key, value):
    lock.acquire()
    try:
        # Save to memcached (expiration up to 30 days)
        mc.set(key, value, 0)
    finally:
        lock.release()

# Remove a item from a list
def remove_from_list(items, target):
    new_items = []
    for item in items:
        if item.ip_address != target.ip_address:
            new_items.append(item)
    return new_items

# Return a list of neighbors' ip addresses
def get_neighbors_ip_list(neighbors):
    neighbors_ip_list = []
    for neighbor in neighbors:
        neighbors_ip_list.append(neighbor.ip_address)
    return neighbors_ip_list

# Check if new peer is already in
def is_in_neighbors(neighbors_ip_list, new_peer_ip_address):
    if new_peer_ip_address in neighbors_ip_list:
        return True
    else:
        return False

# Remove duplicated neighbor
def remove_neighbors_with_same_ip(neighbors):

    new_neighbors = []
    for i in range(len(neighbors)):
        neighbors_ip_list = get_neighbors_ip_list(new_neighbors)
        if neighbors[i].ip_address not in neighbors_ip_list:
            new_neighbors.append(neighbors[i])
    return new_neighbors

# Randomly pick n neighbors
def pick_neighbors_at_random(neighbors, number):

    # Select a cloud at random
    random_neighbors = []
    for i in range(number):
        neighbor =  random.choice(neighbors)
        random_neighbors.append(neighbor)

    return random_neighbors


def filter_received_neighbor_response(neighbors, received_neighbors):
    
    # Discard entries pointing to agent, and entries that are already in anget's cache
    filtered_received_neighbors = []
    neighbors_ip_list = get_neighbors_ip_list(neighbors)

    for neighbor in received_neighbors:
        #if neighbor['ip_address'] not in neighbors_ip_list and neighbor['ip_address'] != AGENT_IP:
        if neighbor['ip_address'] != AGENT_IP:
            neighbor = Neighbor(neighbor['ip_address'], int(neighbor['age']))
            filtered_received_neighbors.append(neighbor)
    
    # Remove redundant neighbors	
    filtered_received_neighbors = remove_neighbors_with_same_ip(filtered_received_neighbors)

    return filtered_received_neighbors

# Update local neighbros list based on list of neighbros received and sent
def update_neighbors_cache(received_neighbors, selected_neighbors):

    neighbors = read_from_memory_cache("neighbors")
 
    filtered_received_neighbors = filter_received_neighbor_response(neighbors, received_neighbors)

    # Update peer's cache to include all remaining entries 
    # Firstly, use empty cache slots (if any)
    #if len(neighbors) < FIXED_SIZE_CACHE:
    if len(read_from_memory_cache("neighbors")) < FIXED_SIZE_CACHE:

        for i in range(FIXED_SIZE_CACHE-len(neighbors)):
            if len(filtered_received_neighbors) != 0 and len(neighbors) < FIXED_SIZE_CACHE:
                neighbors_ip_list = get_neighbors_ip_list(neighbors)
                random_neighbor = random.choice(filtered_received_neighbors)
                if not is_in_neighbors(neighbors_ip_list, random_neighbor.ip_address):
                    neighbors.append(random_neighbor)
                    filtered_received_neighbors = remove_from_list(filtered_received_neighbors, random_neighbor)
            else:
                break

    
    #print '$'*100
    #for neighbor in selected_neighbors:
    #    print '%s, %s' % (neighbor.ip_address, neighbor.age)
    #print '$'*100

    # Secondly, replace entries among the ones originally sent to the other peer
    #if len(neighbors) == FIXED_SIZE_CACHE:
    if len(read_from_memory_cache("neighbors")) == FIXED_SIZE_CACHE:
        #response_neighbors_cp = response_neighbors
        for i in range(len(filtered_received_neighbors)):

            if len(selected_neighbors) == 0:
                break

            #if len(read_from_memory_cache("neighbors")) == FIXED_SIZE_CACHE:
              	#neighbors_ip_list = get_neighbors_ip_list(neighbors)
            neighbors_ip_list = get_neighbors_ip_list(neighbors)
            random_neighbor = random.choice(filtered_received_neighbors)
            random_selected_neighbor = random.choice(selected_neighbors)

            if not is_in_neighbors(neighbors_ip_list, random_neighbor.ip_address):

                filtered_received_neighbors = remove_from_list(filtered_received_neighbors, random_neighbor)
            	selected_neighbors = remove_from_list(selected_neighbors, random_selected_neighbor)
            	neighbors = remove_from_list(neighbors, random_selected_neighbor)

            	neighbors.append(random_neighbor)
            else:
                break
    #print '$'*100
    
    write_to_memory_cache("neighbors", neighbors)




