import os, time
# import setup
from flask import Flask, render_template, url_for, request, make_response
from boto.mturk.connection import MTurkConnection
from boto.mturk.question import ExternalQuestion
from boto.mturk.qualification import Qualifications, PercentAssignmentsApprovedRequirement, NumberHitsApprovedRequirement
from boto.mturk.price import Price

import boto3
import Queue
import pickle, math
import requests
from datetime import datetime

import numpy as np
from util import *
from triangular_walk import check_triangle_completion

import argparse

parser = argparse.ArgumentParser(description='Simulated Triangular Walk Experiment.')
parser.add_argument('-assignment', '--num_assignments', help='Number of assignments per HIT', type=int)
parser.add_argument('-hits', '--num_hits', help='Number of HITs', type=int)
parser.add_argument('-n_max', '--n_max', help='Triangle depth', type=int)
parser.add_argument('-qsize', '--queue_size', help='Server-side priority queue size', type=int)
parser.add_argument('-n_rep', '--n_rep', help='Simulation repetetions', type=int)
parser.add_argument('-est_type', '--estimator_type', 
                    help='Estimation technique (default=0)\n 0: TriangularWalk, 1: VOTING', default=0, type=int)

# APIs to in-house server.
def write_to_file(file, elements):
    with open(file, 'a+') as f:
        for elem in elements:
            f.write(elem + '\n')

def post_HITs(num_assignments, num_hits):
    hit_ids_ = range(num_hits)
    return hit_ids_

def update_queue(url, new_elements, track_id):
    for e in new_elements:
        params = {'n':e[0], 'sidx':e[1], 'k':e[2], 'issued_id':e[3], 'track_id':track_id}
        r = requests.get(url=url + '/update', params=params)
    return

def check_queue(url, new_elements, track_id):
    new_elements_ = list()
    for e in new_elements:
        params = {'n':e[0], 'sidx':e[1], 'k':e[2], 'issued_id':e[3], 'track_id':track_id}
        r = requests.get(url=url+'/check', params=params)
        if r.text == 'False':
            new_elements_.append(e)
    return new_elements_

def reset_queue(url, track_id):
    r = requests.get(url=url+'/reset', params={'track_id':track_id})
    return r.text

def init_server(url, num_tracks):
    r = requests.get(url=url+'/init', params={'num_tracks':num_tracks})
    return r.text

# Main experiment codes.
if __name__ == "__main__":
    external_url = "http://127.0.0.1:5000"
    
    args = parser.parse_args()
    est_type = args.estimator_type
    num_assignments = args.num_assignments 
    num_hits = args.num_hits # number of hits also define the number of tracks
    n_max = args.n_max 
    queue_size = args.queue_size 
    n_rep = args.n_rep 
    timeout = 10 # watiting time until timeout for each assignment taken by worker
    batch_size = 10

    data, label = load_restaurant_dataset()
    n_items = len(data)

    # to put back any timeouted items
    issued = dict() # issued_id -> ( (n_, sidx_, k_, issued_id), issued_time )
    issued_id = 0 # can also be used as total triangular walks counter

    # Initialize
    print init_server(external_url, num_hits)
    hit_ids = list(range(num_hits))

    for r_ in range(n_rep):
        # final estimates are the means of means of multiple tracks/experiments.
        estimates = dict() # num_responses -> number of estimated errors (for plotting)
        cur_estimates = dict() # hold estimates by all completed triangles per track
        cur_estimates_by_sidx = dict() # hold estimates by sidx
        issued_id = 0

        for track_id in range(num_hits):
            cur_estimates[track_id] = list()
            reset_queue(external_url, track_id)

            pqueue_ = list() # later, this is converted to PriorityQueue on the server-side
            for i in range(queue_size):
                issued_id += 1
                n_, k_ = 0, 0 # num_votes, num_positives
                sidx_ = np.random.choice(len(data))
                pqueue_.append((n_, sidx_, k_, issued_id))
                issued[issued_id] = ( (n_, sidx_, k_, issued_id), time.time(), track_id )
            update_queue(external_url, pqueue_, track_id)

        #hit_ids = post_HITs(num_assignments, num_hits)
        last_submit_time = dict()
        for hit_id in hit_ids:
            last_submit_time[hit_id] = time.time()

        start_time = time.time()
        num_responses = 0
        while num_responses < num_hits * num_assignments * batch_size and time.time() - start_time < 60*60*1: # timeout for a single experiment (1 hour)
            results = list()
            results = get_results_simulated(hit_ids, batch_size)

            new_elements = dict()
            for r in results:
                hit_id_ = r['hit_id']
                output_ = r['output'] # v1_is_valid_
                submit_time_ = r['submit_time']
                issued_id_ = r['issued_id']
                track_id_ = r['track_id']
                n_, sidx_, k_ = r['n'], r['sidx'], r['k']
                
                n_ += 1
                if output_ == 'yes':
                    k_ += 1

                if last_submit_time[hit_id_] < submit_time_:
                    if issued_id_ in issued:
                        del issued[issued_id_]

                    last_submit_time[hit_id_] = submit_time_
                    num_responses += 1

                    if track_id_ not in new_elements:
                        new_elements[track_id_] = list()

                    if est_type == 0:
                        # check if this new response has completed a triangle
                        completed_, estimate_ = check_triangle_completion(n_, k_, n_max=n_max)
                        if completed_:
                            # estimate with num_responses
                            if track_id_ not in cur_estimates:
                                cur_estimates[track_id_] = list()
                            cur_estimates[track_id_].append(estimate_)

                            # add a new item
                            issued_id += 1 # original counter
                            issued_id_ = issued_id
                            n_, sidx_, k_ = 0, np.random.choice(len(data)), 0
                        issued[issued_id_] = ( (n_, sidx_, k_, issued_id_), time.time(), track_id_ )
                        new_elements[track_id_].append( (n_, sidx_, k_, issued_id_) )

                        if len(cur_estimates) > 0:
                            est_ = np.mean([np.mean(track_est_) for track_est_ in cur_estimates.values() if len(track_est_)>0])
                            estimates[num_responses/batch_size] = est_ * n_items 

                    elif est_type == 1:
                        if sidx_ in cur_estimates_by_sidx:
                            n__, k__ = cur_estimates_by_sidx[sidx_]
                            cur_estimates_by_sidx[sidx_] = (n__ + n_, k__ + k_)
                        else:
                            cur_estimates_by_sidx[sidx_] = (n_, k_)
                        # add a new item
                        issued_id += 1 # original counter
                        issued_id_ = issued_id
                        n_, sidx_, k_ = 0, np.random.choice(len(data)), 0
                        issued[issued_id_] = ( (n_, sidx_, k_, issued_id_), time.time(), track_id_ )
                        new_elements[track_id_].append( (n_, sidx_, k_, issued_id_) )

                        if len(cur_estimates_by_sidx) > 0:
                            est_ = np.sum([n__/2 < k__ for n__, k__ in cur_estimates_by_sidx.values()])
                            estimates[num_responses/batch_size] = est_
            

            for k, v in issued.iteritems():
                if time.time() - v[1] > timeout:
                    issued[k] = ( v[0], time.time(), v[2] )
                    if v[2] not in new_elements:
                        new_elements[v[2]] = [v[0]]
                    else:
                        new_elements[v[2]] += [ v[0] ]

            for k, v in new_elements.iteritems():
                v_ = check_queue(external_url, v, k)
                update_queue(external_url, v_, k)
            
            print('num_assignments:', num_responses/batch_size, '/', num_hits*num_assignments)
        
        if est_type == 0:
            pickle.dump(estimates, open('results/restaurant_estimates_simulated%s.p'%(r_),'wb'))
        elif est_type == 1:
            pickle.dump(estimates, open('results/restaurant_estimates_simulated_voting%s.p'%(r_),'wb'))

    
