import os
from flask import Flask, render_template, url_for, request, make_response
from boto.mturk.connection import MTurkConnection
from boto.mturk.question import ExternalQuestion
from boto.mturk.qualification import Qualifications, PercentAssignmentsApprovedRequirement, NumberHitsApprovedRequirement
from boto.mturk.price import Price

import numpy as np
import argparse, os, sys, os.path, csv, json
import math
import pickle
from boto.mturk.price import Price
from boto.mturk.question import HTMLQuestion
from boto.mturk.connection import MTurkRequestError
import io
import boto3, botocore
import pickle
import Queue
import random, string
import copy
import time
import threading

from util import * 

from rq import Queue as rQueue
from worker import conn

#Start Configuration Variables
AWS_ACCESS_KEY_ID = "AKIAJE4YCRH44M4ND7JA"
AWS_SECRET_ACCESS_KEY = "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"
DEV_ENVIROMENT_BOOLEAN = False
DEBUG = True
#End Configuration Variables

#This allows us to specify whether we are pushing to the sandbox or live site.
if DEV_ENVIROMENT_BOOLEAN:
    AMAZON_HOST = "https://workersandbox.mturk.com/mturk/externalSubmit"
else:
    AMAZON_HOST = "https://www.mturk.com/mturk/externalSubmit"

app = Flask(__name__, static_url_path='')

filename = 'pqueue.p'
filename_update = 'new_elements.p'
bucket_name = 'dqm'
data, label, items_by_label = load_restaurant_dataset()

# num_workers = Queue.PriorityQueue()
pqueues = dict()
rqueue = rQueue(connection=conn)
pqueues_lock = threading.RLock()
# num_worker_lock = threading.RLock()
tracker = 0

@app.route('/init', methods=['GET', 'POST'])
def init():
    global pqueues
    # global num_workers
    num_tracks_ = int(request.args.get('num_tracks'))
    
    with pqueues_lock:
        for i in range(num_tracks_):
            pqueues[i] = Queue.PriorityQueue()
    # with num_worker_lock:
    #     for i in range(num_tracks_):
    #         num_workers.put((0,i))
    if len(pqueues) == num_tracks_:
        return 'Server initializaed', 200, {'Content-Type': 'text/css; charset=utf-8'}
    else:
        return 'Initialization failed', 500, {'Content-Type': 'text/css; charset=utf-8'}


# @app.route('/check', methods=['GET', 'POST'])
# def check_queue():
#     global pqueues
#     n_ = request.args.get('n')
#     sidx_ = request.args.get('sidx')
#     k_ = request.args.get('k')
#     issued_id_ = int(request.args.get('issued_id'))
#     track_id_ = int(request.args.get('track_id'))
#     item_ = (-1 * int(n_), int(sidx_), int(k_), int(issued_id_))
    
#     if track_id_ not in pqueues:
#         return 'False', 200, {'Content-Type': 'text/css; charset=utf-8'}

#     queue_ = pqueues[track_id_]    
#     is_present = item_[3] in [p_[3] for p_ in queue_.queue]
    
#     return '%s'%is_present, 200, {'Content-Type': 'text/css; charset=utf-8'}

@app.route('/update', methods=['GET', 'POST'])
def update_queue():
    global pqueues
    with pqueues_lock:
        n_ = request.args.get('n')
        sidx_ = request.args.get('sidx')
        k_ = request.args.get('k')
        issued_id_ = request.args.get('issued_id')
        track_id_ = int(request.args.get('track_id'))
        item_ = (-1*int(n_), (int(n_), int(sidx_), int(k_), int(issued_id_)))
        #item_ = (int(n_), int(sidx_), int(k_), int(issued_id_))
        
        if track_id_ in pqueues:
            pqueues[track_id_].put(item_)
        else:
            return 'update failed on %s'%track_id_, 500, {'Content-Type': 'text/css; charset=utf-8'}
        return 'update_queue( %s, %s, %s, %s ) track %s'%(n_,sidx_,k_, issued_id_, track_id_), 200, {'Content-Type': 'text/css; charset=utf-8'}


@app.route('/work', methods=['GET', 'POST'])
def work():
    global pqueues
    global num_workers
    global data
    global label
    global items_by_label
    
    #The following code segment can be used to check if the turker has accepted the task yet
    if request.args.get("assignmentId") == "ASSIGNMENT_ID_NOT_AVAILABLE":
        #Our worker hasn't accepted the HIT (task) yet
        return 'Please accept the HIT from the dashboard.'
    else:
        #Our worker accepted the task
        pass

    num_items = 10
    track_id_ =  int(request.args.get('trackId'))
    
    with pqueues_lock:
        while True:
            if track_id_ in pqueues:
                queue_ = pqueues[track_id_]
                break
            else:
                return 'Server temporarily down, please try again in a few minutes', 503, {'Content-Type': 'text/css; charset=utf-8'}
                
    #print 'work on', track_id_

    batch = list()
    honeypot1_pos = np.random.choice(12) # yes
    honeypot2_pos = (honeypot1_pos + 4)%12 # no
    cnt = 0
    for i in range(num_items+2): # num_items + 2 honeypots
        if i == honeypot1_pos:
            pos = np.random.choice(len(items_by_label[1]))
            t = (0, pos, 0, -2)
        elif i == honeypot2_pos:
            pos = np.random.choice(len(items_by_label[0]))
            t = (0, pos, 0, -3)
        else:    
            try:
                if cnt < 5:
                    t = queue_.get(block=False)[1]
                    cnt += 1
                else:
                    t = None
            except Queue.Empty:
                t = None
        batch.append(t)

    render_data = {
        "worker_id": request.args.get("workerId"),
        "assignment_id": request.args.get("assignmentId"),
        "amazon_host": AMAZON_HOST,
        "hit_id": request.args.get("hitId"),
        "track_id": track_id_,
        "honeypot1": "v%s_option1"%(honeypot1_pos+1),
        "honeypot2": "v%s_option2"%(honeypot2_pos+1)
    }
    
    # random_items = list()
    for idx in range(len(batch)):
        t = batch[idx]
        n_, sidx_, k_, issued_id_ = -1, -1, -1, -1
        if t is None:
            sidx_ = np.random.choice(len(data))
            # while sidx_ in random_items:
            #     sidx_ = np.random.choice(len(data))
            # random_items.append(sidx_)
            n_, k_ = 0, 0
            #item_pair_ = 'Please click *no* to this empty question<br/>-'
        else:
            n_, sidx_, k_, issued_id_ = t[0], t[1], t[2], t[3]

        if issued_id_ == -2:
            item_pair_ = items_by_label[1][t[1]]
        elif issued_id_ == -3:
            item_pair_ = items_by_label[0][t[1]]
        else:
            item_pair_ = data[sidx_]

        q = (item_pair_, n_, sidx_, k_, issued_id_)
        
        render_data["q%s_a"%(idx+1)] = q[0].split('<br/>')[0]
        render_data["q%s_b"%(idx+1)] = q[0].split('<br/>')[1]
        render_data["n_%s"%(idx+1)] = q[1]
        render_data["sidx_%s"%(idx+1)] = q[2]
        render_data["k_%s"%(idx+1)] = q[3]
        render_data["issued_id_%s"%(idx+1)] = q[4]

    resp = make_response(render_template("restaurant_tmpl_%s.html"%len(batch), name = render_data))
    
    resp.headers['x-frame-options'] = 'this_can_be_anything'
    return resp

@app.route('/test', methods=['GET', 'POST'])
def test():
    global pqueues
    global tracker

    num_tracks = int(request.args.get('num_tracks'))
    num_items = int(request.args.get('num_items'))
    worker_quality = float(request.args.get('worker_quality'))
    track_id_ = tracker % num_tracks
    tracker += 1
    
    queue_ = pqueues[track_id_]

    batch = list()
    honeypot1_pos = np.random.choice(12) # yes
    honeypot2_pos = (honeypot1_pos + 4)%12 # no
    cnt = 0
    for i in range(num_items+2): # num_items + 2 honeypots
        if i == honeypot1_pos:
            pos = np.random.choice(len(items_by_label[1]))
            t = (0, pos, 0, -2)
        elif i == honeypot2_pos:
            pos = np.random.choice(len(items_by_label[0]))
            t = (0, pos, 0, -3)
        else:    
            try:
                if cnt < 5:
                    t = queue_.get(block=False)[1]
                    cnt += 1
                else:
                    t = None
            except Queue.Empty:
                t = None
        batch.append(t)

    items = list()
    for i in range(len(batch)):
        # ideal response with ground truth
        '''
            var output = {
                v1_is_valid: v1_is_valid,
                sidx: sidx,
                n: n,
                k: k,
                issued_id: issued_id,
                track_id: track_id
            };
        '''
        
        if batch[i] is None:
            n_, sidx_, k_, issued_id_ = 0, np.random.choice(len(data)), 0, -1
        else:
            n_, sidx_, k_, issued_id_ = batch[i]
        label_ = label[data[int(sidx_)]]
        if np.random.random() < worker_quality:
            v1_is_valid_ = 'no'
            if label_ == 1:
                v1_is_valid_ = 'yes'
        else:
            v1_is_valid_ = 'yes'
            if label_ == 1:
                v1_is_valid_ = 'no'
        
        resp = {"v1_is_valid":v1_is_valid_, "sidx":sidx_, "n":n_, "k":k_, "issued_id":issued_id_, "track_id":track_id_}
        items.append(resp)
    response = {'items':items}
    response['AssignmentId'] = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    response['WorkerId'] = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))

    return json.dumps(response)


@app.route('/', methods=['GET', 'POST'])
def main():
    # global num_workers
    global tracker
    num_items = 10 
    num_tracks = 5
    
    #The following code segment can be used to check if the turker has accepted the task yet
    if request.args.get("assignmentId") == "ASSIGNMENT_ID_NOT_AVAILABLE":
        #Our worker hasn't accepted the HIT (task) yet
        render_data = {
            "worker_id": request.args.get("workerId"),
            "assignment_id": request.args.get("assignmentId"),
            "amazon_host": AMAZON_HOST,
            "heroku_app": "https://dqm-01.herokuapp.com/work",
            "hit_id": request.args.get("hitId"),
            "track_id": -1
        }
    else:
        #Our worker accepted the task
        track_id_ = tracker % num_tracks
        tracker += 1
        render_data = {
            "worker_id": request.args.get("workerId"),
            "assignment_id": request.args.get("assignmentId"),
            "amazon_host": AMAZON_HOST,
            "heroku_app": "https://dqm-01.herokuapp.com/work",
            "hit_id": request.args.get("hitId"),
            "track_id": track_id_
        }

    resp = make_response(render_template("preview.html", name = render_data))

    #This is particularly nasty gotcha.
    #Without this header, your iFrame will not render in Amazon
    resp.headers['x-frame-options'] = 'this_can_be_anything'
    return resp

if __name__ == "__main__":
    app.debug = DEBUG
    app.run() 
