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
from switch import switch

import argparse

parser = argparse.ArgumentParser(description='Simulated Triangular Walk Experiment.')
parser.add_argument('-assignment', '--num_assignments', help='Number of assignments per HIT', type=int)
parser.add_argument('-hits', '--num_hits', help='Number of HITs', type=int)
parser.add_argument('-n_max', '--n_max', help='Triangle depth', default=5, type=int)
parser.add_argument('-n_rep', '--n_rep', help='Simulation repetetions', type=int)
parser.add_argument('-w', '--worker_quality', help='Worker quality (default=1.0)', default=1.0, type=float)
parser.add_argument('-est_type', '--estimator_type', 
                    help='Estimation technique (default=0)\n 0: TriangularWalk, 1: VOTING, 2: SWITCH', default=0, type=int)

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

def init_server(url, num_tracks):
    r = requests.get(url=url+'/init', params={'num_tracks':num_tracks})
    return r.text

# Main experiment codes.
if __name__ == "__main__":
    external_url = "http://127.0.0.1:5000"
    
    args = parser.parse_args()
    est_type = args.estimator_type
    worker_quality = args.worker_quality
    num_assignments = args.num_assignments 
    num_hits = args.num_hits # number of hits also define the number of tracks
    n_max = args.n_max 
    n_rep = args.n_rep 
    #timeout = 420 # watiting time until timeout for each assignment taken by worker
    batch_size = 10

    data, label, _ = load_restaurant_dataset()
    n_items = len(data)


    # Initialize
    print init_server(external_url, num_hits)
    hit_ids = list(range(num_hits))

    for r_ in range(n_rep):

        # this representation is for SWITCH estimator
        data_matrix = np.zeros((len(data), num_hits * num_assignments)) + -1        

        # to put back any timeouted items
        items_by_track = dict()
        issued = dict() # issued_id -> ( (n_, sidx_, k_, issued_id), issued_time )
        issued_id = 0 # can also be used as total triangular walks counter
        # final estimates are the means of means of multiple tracks/experiments.
        estimates = dict() # num_responses -> number of estimated errors (for plotting)
        cur_estimates = dict() # hold estimates by all completed triangles per track
        cur_estimates_by_sidx = dict() # hold estimates by sidx
        issued_id = 0

        start_time = time.time()
        num_responses = 0 # each assignment holds batct_size responses
        assignment_cnt = -1
        assignment_checker = set()
        
        empty_track = set()
        checker = set()
        worker_checker = dict()
        while num_responses < num_hits * num_assignments * batch_size and time.time() - start_time < 60*60*5:
            has_progressed = False
            results = list()
            results = get_results_simulated(hit_ids,  checker, num_hits, worker_quality, batch_size=batch_size)
        
            new_elements = dict()
            for r in results: 
                issued_id_ = r['issued_id']
                track_id_ = r['track_id']
                
                hit_id_ = r['hit_id']
                output_ = r['output'] # v1_is_valid_
                
                n_, sidx_, k_ = r['n'], r['sidx'], r['k']

                if issued_id_ == -1:
                    issued_id += 1 # original counter
                    issued_id_ = issued_id
                    r['issued_id'] = issued_id_
                elif issued_id_ in issued:
                    n_ = max(n_, issued[issued_id_][0][0])
                    k_ = max(k_, issued[issued_id_][0][2])
                    del issued[issued_id_]
                else:
                    continue

                n_ += 1
                v_ = 0
                if output_ == 'yes':
                    k_ += 1
                    v_ = 1
                
                has_progressed = True

                num_responses += 1
                #write_to_file2(log_file, ','.join([str(rv_) for rv_ in r.values()]))

                # for SWITCH estimator
                if r['assignment_id'] not in assignment_checker:
                    assignment_checker.add(r['assignment_id'])
                    assignment_cnt += 1
                if assignment_cnt < data_matrix.shape[1]:
                    data_matrix[sidx_][assignment_cnt] = v_

                if est_type == 0:
                    # check if this new response has completed a triangle
                    completed_, estimate_ = check_triangle_completion(n_, k_, n_max=n_max)
                    if completed_:
                        # estimate with num_responses
                        if track_id_ not in cur_estimates:
                            cur_estimates[track_id_] = list()
                        cur_estimates[track_id_].append(estimate_)

                        # add a new item. we now sample at the server.
                        #issued_id += 1 # original counter
                        #issued_id_ = issued_id
                        #n_, sidx_, k_ = 0, np.random.choice(len(data)), 0 
                    else:
                        update_queue(external_url, [(n_, sidx_, k_, issued_id_)], track_id_)
                        new_elements[issued_id_] =  ( (n_, sidx_, k_, issued_id_), time.time(), track_id_ )
                        #issued[issued_id_] = ( (n_, sidx_, k_, issued_id_), time.time(), track_id_ )

                    if num_responses%(batch_size*40) == 0:
                        est_ = np.mean([np.mean(track_est_) for track_est_ in cur_estimates.values() if len(track_est_) > 0])
                        estimates[num_responses/batch_size] = est_ * n_items
                elif est_type == 1:
                    if sidx_ in cur_estimates_by_sidx:
                        n__, k__ = cur_estimates_by_sidx[sidx_]
                        cur_estimates_by_sidx[sidx_] = (n__ + n_, k__ + k_)
                    else:
                        cur_estimates_by_sidx[sidx_] = (n_, k_)
                    # add a new item
                    # issued_id += 1 # original counter
                    # issued_id_ = issued_id
                    # n_, sidx_, k_ = 0, np.random.choice(len(data)), 0
                    # update_queue(external_url, [(n_, sidx_, k_, issued_id_)], track_id_)
                    # new_elements[issued_id_] =  ( (n_, sidx_, k_, issued_id_), time.time(), track_id_ )
                    # #issued[issued_id_] = ( (n_, sidx_, k_, issued_id_), time.time(), track_id_ )

                    if num_responses%(batch_size*40) == 0:
                        est_ = np.sum([n__/2 < k__ for n__, k__ in cur_estimates_by_sidx.values()])
                        estimates[num_responses/batch_size] = est_
                elif est_type == 2:
                    if num_responses%(batch_size*40) == 0:
                        est_ = switch(data_matrix[:,:assignment_cnt])
                        estimates[num_responses/batch_size] = est_
                    

            # send back any missed items
            for k, v in issued.iteritems():
                update_queue(external_url, [v[0]] , v[2])
            for k, v in new_elements.iteritems():
                issued[k] = v
            
            #time.sleep(20)

            if has_progressed:
                print('num_assignments:', num_responses/batch_size, '/', num_hits*num_assignments)
        
        if est_type == 0:
            pickle.dump(estimates, open('results/restaurant_estimates_simulated%s.p'%(r_),'wb'))
        elif est_type == 1:
            pickle.dump(estimates, open('results/restaurant_estimates_simulated_voting%s.p'%(r_),'wb'))
        elif est_type == 2:
            pickle.dump(estimates, open('results/restaurant_estimates_simulated_switch%s.p'%(r_),'wb'))
    
