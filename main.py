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

from util import * 

from rq import Queue as rQueue
from worker import conn

#Start Configuration Variables
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
data, label = load_restaurant_dataset()

num_workers = Queue.PriorityQueue()
pqueues = dict()
rqueue = rQueue(connection=conn)

@app.route('/init', methods=['GET', 'POST'])
def init():
    global pqueues
    global num_workers
    num_tracks_ = int(request.args.get('num_tracks'))
    for i in range(num_tracks_):
        pqueues[i] = Queue.PriorityQueue()
        num_workers.put((0,i))

    return 'Server initializaed', 200, {'Content-Type': 'text/css; charset=utf-8'}

@app.route('/check', methods=['GET', 'POST'])
def check_queue():
    global pqueues
    n_ = request.args.get('n')
    sidx_ = request.args.get('sidx')
    k_ = request.args.get('k')
    issued_id_ = int(request.args.get('issued_id'))
    track_id_ = int(request.args.get('track_id'))
    item_ = (-1 * int(n_), int(sidx_), int(k_), int(issued_id_))
    
    if track_id_ not in pqueues:
        return 'False', 200, {'Content-Type': 'text/css; charset=utf-8'}

    queue_ = pqueues[track_id_]    
    is_present = item_[3] in [p_[3] for p_ in queue_.queue]
    
    return '%s'%is_present, 200, {'Content-Type': 'text/css; charset=utf-8'}

@app.route('/update', methods=['GET', 'POST'])
def update_queue():
    global pqueues
    n_ = request.args.get('n')
    sidx_ = request.args.get('sidx')
    k_ = request.args.get('k')
    issued_id_ = request.args.get('issued_id')
    track_id_ = int(request.args.get('track_id'))
    item_ = (-1 * int(n_), int(sidx_), int(k_), int(issued_id_))
    
    if track_id_ not in pqueues:
        pqueues[track_id_] = Queue.PriorityQueue()
    queue_ = pqueues[track_id_]
    queue_.put(item_)

    return 'update_queue( %s, %s, %s, %s ) track %s qsize %s'%(n_,sidx_,k_, issued_id_, track_id_, queue_.qsize()), 200, {'Content-Type': 'text/css; charset=utf-8'}

@app.route('/work', methods=['GET', 'POST'])
def work():
    global pqueues
    global num_workers
    global data
    global label
    
    num_items = 10
    #track_id_ = int(request.args.get('trackId'))
    n_w_, track_id_ = -1, -1
    try:
        n_w_, track_id_ = num_workers.get()
        num_workers.put((n_w_+1, track_id_))
    except Queue.Empty:
        print 'num_workers empty in work()??'
        return 'Server temporarily down, please try again in a few minutes', 200, {'Content-Type': 'text/css; charset=utf-8'}
    
    queue_ = pqueues[track_id_]
    batch = list()
    honeypot = -1
    for i in range(num_items):
        try:
            t = queue_.get(block=False)
            if label[data[t[1]]] == 1:
                honeypot = i+1
        except Queue.Empty:
            t = None
        batch.append(t)

    render_data = {
        "worker_id": request.args.get("workerId"),
        "assignment_id": request.args.get("assignmentId"),
        "amazon_host": AMAZON_HOST,
        "hit_id": request.args.get("hitId"),
        "track_id": track_id_,
        "honeypot": "v%s_option1"%honeypot
    }
    for idx in range(len(batch)):
        t = batch[idx]
        if t is None:
            n_, sidx_, k_, issued_id_ = -1, -1, -1, -1
            item_pair_ = 'Please click *no* to this empty question<br/>-'
        else:
            n_, sidx_, k_, issued_id_ = t[0], t[1], t[2], t[3]
            n_ = -1 * int(n_)
            item_pair_ = data[sidx_]

        q = (item_pair_, n_, sidx_, k_, issued_id_)
        
        render_data["q%s_a"%(idx+1)] = q[0].split('<br/>')[0]
        render_data["q%s_b"%(idx+1)] = q[0].split('<br/>')[1]
        render_data["n_%s"%(idx+1)] = q[1]
        render_data["sidx_%s"%(idx+1)] = q[2]
        render_data["k_%s"%(idx+1)] = q[3]
        render_data["issued_id_%s"%(idx+1)] = q[4]
    
    #render_data = rqueue.enqueue(work_helper, render_data, batch, data)

    resp = make_response(render_template("restaurant_tmpl_%s.html"%num_items, name = render_data))
    
    resp.headers['x-frame-options'] = 'this_can_be_anything'
    return resp

@app.route('/test', methods=['GET', 'POST'])
def test():
    global pqueues
    global num_workers

    num_items = int(request.args.get('num_items'))

    n_w_, track_id_ = -1, -1
    try:
        n_w_, track_id_ = num_workers.get()
        num_workers.put((n_w_+1, track_id_))
    except Queue.Empty:
        return 'Server temporarily down, please try again in a few minutes', 200, {'Content-Type': 'text/css; charset=utf-8'}
    
    queue_ = pqueues[track_id_]
    batch = list()
    for i in range(num_items):
        try:
            t = queue_.get(block=False)
        except Queue.Empty:
            t = None
        batch.append(t)

    items = list()
    for i in range(num_items):
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
            n_, sidx_, k_, issued_id_ = -1, -1, -1, -1
            v1_is_valid_ = 'no'
        else:
            n_, sidx_, k_, issued_id_ = batch[i]
            n_ = -1 * int(n_)
            label_ = label[data[int(sidx_)]]
            v1_is_valid_ = 'no'
            if label_ == 1:
                v1_is_valid_ = 'yes'
        
        resp = {"v1_is_valid":v1_is_valid_, "sidx":sidx_, "n":n_, "k":k_, "issued_id":issued_id_, "track_id":track_id_}
        items.append(resp)

    return json.dumps(items)

@app.route('/reset', methods=['GET', 'POST'])
def reset():
    global pqueues
    track_id_ = int(request.args.get('track_id'))
    queue_ = pqueues[track_id_]
    queue_.queue.clear()
    return 'Reset queue', 200, {'Content-Type': 'text/css; charset=utf-8'}

@app.route('/', methods=['GET', 'POST'])
def main():
    num_items = 10 
    
    #The following code segment can be used to check if the turker has accepted the task yet
    if request.args.get("assignmentId") == "ASSIGNMENT_ID_NOT_AVAILABLE":
        #Our worker hasn't accepted the HIT (task) yet
        pass
    else:
        #Our worker accepted the task
        pass

    render_data = {
        "worker_id": request.args.get("workerId"),
        "assignment_id": request.args.get("assignmentId"),
        "amazon_host": AMAZON_HOST,
        "heroku_app": "https://dqm-01.herokuapp.com/work",
        "hit_id": request.args.get("hitId"),
        "track_id": -1
    }

    resp = make_response(render_template("preview.html", name = render_data))

    #This is particularly nasty gotcha.
    #Without this header, your iFrame will not render in Amazon
    resp.headers['x-frame-options'] = 'this_can_be_anything'
    return resp

if __name__ == "__main__":
    app.debug = DEBUG
    app.run() 
