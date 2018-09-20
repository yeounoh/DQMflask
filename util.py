import csv, os, sys, json
import io, time
import pickle
from boto.mturk.price import Price
from boto.mturk.question import HTMLQuestion
from boto.mturk.connection import MTurkRequestError
import requests

def work_helper(render_data, batch, data):

    for idx in range(len(batch)):
        t = batch[idx]
        if t is None:
            n_, sidx_, k_, issued_id_ = -1, -1, -1, -1
            item_pair_ = 'Please click *no* to this empty question'
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

    return render_data

def load_restaurant_dataset():
    file_path = 'examples/restaurant/restaurant.csv'

    records = {}
    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            gid = str(row[1])
            rid = str(row[0])
            name = row[2] + ', ' + row[3] + ', ' + row[4] + ', ' + row[5]
            records[rid] = (gid, name)

    rest = list()
    label = dict()
    hard_pairs = pickle.load(open('examples/restaurant/hard_pairs.p','rb'))
    for p in hard_pairs:
        candidate = "Address 1) %s<br/>Address 2) %s"%(records[p[0][0]][1], records[p[0][1]][1])
        rest.append(candidate)
        if records[p[0][0]][0] == records[p[0][1]][0]:
            label[rest[-1]] = 1
        else:
            label[rest[-1]] = 0

    return rest, label

def get_results_simulated(hit_ids, batch_size=10):
    results = []

    for hit_id in hit_ids:
        #print (hit_id, 'waiting for results')
        results += process_assignments_simulated(hit_id, batch_size)

    return results

def process_assignments_simulated(hit_id, batch_size=10):
    results = []
    num_items = batch_size
    a = requests.get(url="http://127.0.0.1:5000/test", params={'num_items':num_items})

    if a.text == "Server temporariry down, please try again in a few minutes":
        return results
    
    resp = json.loads(a.text)
    for i in range(num_items):
        item = resp[i]
        n_ = int(item['n'])
        k_ = int(item['k'])
        v1_is_valid_ = item['v1_is_valid']
        issued_id_ = int(item['issued_id'])
        track_id_ = int(item['track_id'])

        if issued_id_ == -1:
            print 'issued_id_ = -1'
            continue
        else:
            results.append({
                'sidx': int(item['sidx']),
                'n': n_,
                'k': k_,
                'issued_id': issued_id_,
                'output': v1_is_valid_,
                'submit_time': time.time(),
                'hit_id': hit_id,
                'track_id': track_id_
            })
    return results


def get_results(mtc, hit_ids, batch_size=10):
    results = []
    status = ['Approved', 'Submitted']

    for hit_id in hit_ids:
        #print (hit_id, 'waiting for results')
        results += process_assignments(mtc, hit_id, status, batch_size=batch_size)
    return results

def process_assignments(mtc, hit_id, status, batch_size=10):
    results = []
    page_number = 1

    while True:
        try:
            assignments = mtc.get_assignments(hit_id,page_number=page_number, page_size=100)
            if len(assignments) == 0:
                return results
        except:
            print >> sys.stderr, ('Bad hit_id %s' % str(hit_id))
            return results

        for a in assignments:
            if a.AssignmentStatus in status:
                try:
                    output = json.loads(a.answers[0][0].fields[0])
                except ValueError as e:
                    print >> sys.stderr, ('Bad data from assignment %s (worker %s)'
                                % (a.AssignmentId, a.WorkerId))
                    mtc.reject_assignment(a.AssignmentId, feedback='Invalid results')
                    continue
                
                for i in range(batch_size):
                    sidx_ = int(json.loads(a.answers[0][0].fields[0])['sidx_%s'%(i+1)])
                    n_ = int(json.loads(a.answers[0][0].fields[0])['n_%s'%(i+1)])
                    k_ = int(json.loads(a.answers[0][0].fields[0])['k_%s'%(i+1)])
                    v1_is_valid_ = json.loads(a.answers[0][0].fields[0])['v%s_is_valid'%(i+1)]
                    issued_id_ = int(json.loads(a.answers[0][0].fields[0])['issued_id_%s'%(i+1)])
                    track_id_ = int(json.loads(a.answers[0][0].fields[0])['track_id'])

                    if issued_id_ == -1:
                        results.append({
                            'issued_id': issued_id_,
                            'track_id': track_id_
                        })
                    else:
                        results.append({
                            'assignment_id': a.AssignmentId,
                            'hit_id': hit_id,
                            'worker_id': a.WorkerId,
                            'sidx': sidx_,
                            'n': n_,
                            'k': k_,
                            'issued_id': issued_id_,
                            'output': v1_is_valid_,
                            'submit_time': a.SubmitTime,
                            'track_id': track_id_
                        })
            page_number += 1

    return results
