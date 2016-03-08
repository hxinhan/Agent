#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Xin Han <hxinhan@gmail.com>
#
'''
A file to initiate databse
'''

import ConfigParser
from models import *
import sqlalchemy.exc
import ast
import uuid

config = ConfigParser.ConfigParser()
config.read('agent.conf')
DATABASE_NAME = config.get('Database', 'DATABASE_NAME')
DATABASE_USERNAME = config.get('Database', 'DATABASE_USERNAME')
DATABASE_PASSWORD = config.get('Database', 'DATABASE_PASSWORD')
SITES = ast.literal_eval(config.get('Clouds','sites'))
AGENT_SITE_NAME = config.get('Agent', 'site')
AGENT_SITE_IP = SITES[AGENT_SITE_NAME]

# Configuration of DB engine connection
GLANCE_IMAGE_ENGINE_CONNECTION = 'mysql+mysqldb://%s:%s@localhost/glance' % (DATABASE_USERNAME, DATABASE_PASSWORD)
NOVA_FLAVOR_ENGINE_CONNECTION = 'mysql+mysqldb://%s:%s@localhost/nova' % (DATABASE_USERNAME, DATABASE_PASSWORD)
NEUTRON_NETWORK_ENGINE_CONNECTION = 'mysql+mysqldb://%s:%s@localhost/neutron' % (DATABASE_USERNAME, DATABASE_PASSWORD)
NEUTRON_SUBNET_ENGINE_CONNECTION = 'mysql+mysqldb://%s:%s@localhost/neutron' % (DATABASE_USERNAME, DATABASE_PASSWORD)

# Agent DB engine
agentDB_engine = create_engine('mysql+mysqldb://%s:%s@localhost/%s'%(DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME), echo = False)
#agentDB_engine = create_engine('mysql+mysqldb://%s:%s@localhost/%s'%(DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME), pool_recycle=3600, echo = True)


# Create tables in database
def create_tables():
    try:
        Base.metadata.create_all(agentDB_engine)
    except exc:
        print exc.message

# Read data from database
def read_from_DB(connection, table_name, obj):
    # Read uuid of images from glance databse
    read_engine = create_engine(connection, echo = True)
    
    metadata = MetaData(read_engine)
    read_table = Table(table_name, metadata, autoload = True)
    mapper(obj, read_table)
    
    DBSession = sessionmaker(bind = read_engine)
    R_session = DBSession()

    res = R_session.query(obj).all()
    R_session.close()

    return res


# Synchorize agent table with glance (images talbe in glance DB) in terms of uuid
def Sync_Image():
    
    # Read data of image from database  
    res = read_from_DB(GLANCE_IMAGE_ENGINE_CONNECTION, 'images', GlanceImage)

    # Write to image table of agent DB 
    # Create session of image table of agetn DB
    DBSession = sessionmaker(bind = agentDB_engine)
    W_session = DBSession()
    
    for image in res:
        
        # Check if image already exists in agent DB, if image does not exist in agent DB then add it 
        if image.status == "active" and len(W_session.query(Image).filter_by(uuid_cloud=image.id).all()) == 0:
            # Synchorize image uuid to data table of agent 
            new_image = Image(uuid_agent = uuid.uuid4(), uuid_cloud = image.id, cloud_name = AGENT_SITE_NAME, cloud_address = AGENT_SITE_IP)
            # Add instance to session
            W_session.add(new_image)

    try:
        # Commit session    
        W_session.commit()
    except sqlalchemy.exc.IntegrityError, exc:
        reason = exc.message
        if reason.endswith('is not unique'):
            print "%s already exists" % exc.params[0]
            W_session.rollback()
    finally:
        # Close session
        W_session.close()


# Synchorize agent table with flavor table (instance_types table in nova DB) in terms of uuid
def Sync_Flavor():
   
    # Read data of flavor from database  
    res = read_from_DB(NOVA_FLAVOR_ENGINE_CONNECTION, 'instance_types', NovaFlavor)

    # Write to image table of agent DB 
    # Create session of image table of agetn DB
    DBSession = sessionmaker(bind = agentDB_engine)
    W_session = DBSession()
    
    for flavor in res:
        
        # Check if flavor already exists in agent DB, if flavor does not exist in agent DB then add it 
        if flavor.deleted == 0 and len(W_session.query(Flavor).filter_by(uuid_cloud=flavor.flavorid).all()) == 0:
            # Synchorize flavor uuid to data table of agent 
            new_flavor = Flavor(uuid_agent = uuid.uuid4(), uuid_cloud = flavor.flavorid, cloud_name = AGENT_SITE_NAME, cloud_address = AGENT_SITE_IP)
            # Add instance to session
            W_session.add(new_flavor)

    try:
        # Commit session    
        W_session.commit()
    except sqlalchemy.exc.IntegrityError, exc:
        reason = exc.message
        if reason.endswith('is not unique'):
            print "%s already exists" % exc.params[0]
            W_session.rollback()
    finally:
        # Close session
        W_session.close()

# Synchorize agent table with network table (networks table in neutron DB) in terms of uuid
def Sync_Network():
    
    # Read data of network from database  
    res = read_from_DB(NEUTRON_NETWORK_ENGINE_CONNECTION, 'networks', NeutronNetwork)
   
    # Write to subnet table of agent DB 
    # Create session of subnet table of agetn DB
    DBSession = sessionmaker(bind = agentDB_engine)
    W_session = DBSession()
    
    for network in res:
        
        # Check if network already exists in agent DB, if network does not exist in agent DB then add it 
        if network.status == 'ACTIVE' and len(W_session.query(Network).filter_by(uuid_cloud=network.id).all()) == 0:
            # Synchorize subnet uuid to data table of agent 
            new_network = Network(uuid_agent = uuid.uuid4(), uuid_cloud = network.id, cloud_name = AGENT_SITE_NAME, cloud_address = AGENT_SITE_IP)
            # Add instance to session
            W_session.add(new_network)

    try:
        # Commit session    
        W_session.commit()
    except sqlalchemy.exc.IntegrityError, exc:
        reason = exc.message
        if reason.endswith('is not unique'):
            print "%s already exists" % exc.params[0]
            W_session.rollback()
    finally:
        # Close session
        W_session.close()


# Synchorize agent table with subnet table (subnets table in neutron DB) in terms of uuid
def Sync_Subnet():
    
    # Read data of subnet from database  
    res = read_from_DB(NEUTRON_SUBNET_ENGINE_CONNECTION, 'subnets', NeutronSubnet)

    # Write to subnet table of agent DB 
    # Create session of subnet table of agetn DB
    DBSession = sessionmaker(bind = agentDB_engine)
    W_session = DBSession()
    
    for subnet in res:
        
        # Check if network already exists in agent DB, if network does not exist in agent DB then add it 
        if subnet.status == 'ACTIVE' and len(W_session.query(Subnet).filter_by(uuid_cloud=subnet.id).all()) == 0:
            # Synchorize subnet uuid to data table of agent 
            new_subnet = Subnet(uuid_agent = uuid.uuid4(), uuid_cloud = subnet.id, cloud_name = AGENT_SITE_NAME, cloud_address = AGENT_SITE_IP)
            # Add instance to session
            W_session.add(new_subnet)
    
    try:
        # Commit session    
        W_session.commit()
    except sqlalchemy.exc.IntegrityError, exc:
        reason = exc.message
        if reason.endswith('is not unique'):
            print "%s already exists" % exc.params[0]
            W_session.rollback()
    finally:
        # Close session
        W_session.close()
    

if __name__ == '__main__':
    create_tables()
    Sync_Image()
    Sync_Flavor()
    Sync_Network()
    #Sync_Subnet()
