"""
Views for nscope model
"""

from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import url_for
from flask import Flask, request, jsonify, render_template, send_file
from flask_login import LoginManager, current_user, login_user
from werkzeug.exceptions import abort
from sqlalchemy import or_, func
import numpy as np
import requests
import os
import sys


from flaskr import db
from flaskr.nscope.models import *

bp = Blueprint("nscope", __name__)


# Creating a simple index route (this will error because we currently dont have an index.html"j
@bp.route("/index")
def index():
    return render_template("index.html")

@bp.route("/api/get_sequence/<id>/<num_elements>/<modulus>", methods=["GET"])
def get_sequence(id, num_elements, modulus):
    # get database entry
    seq = Sequence.get_seq_by_id(id)

    if seq == None:
        return "Error Invalid sequence: " + str(id)
    
    id = seq.id
    name = seq.name

    vals = np.array(seq.first_100_entries, dtype=np.int64)
    if int(modulus) != 0:
        vals = vals % int(modulus)

    if int(num_elements) < len(vals):
        vals = vals[0:int(num_elements)]

    # jsonify the data
    data = jsonify({'id': id, 'name': name, 'values': vals.tolist()})

    # return the data
    return data

@bp.route("/api/get_oeis_sequence/<oeis_id>/<num_elements>", methods=["GET"])
def get_oeis_seqence(oeis_id, num_elements):
    if not os.path.exists("temp"):
        os.makedirs('temp')
    oeis_filename = "temp/b{}.txt".format(oeis_id[1:])
    if not os.path.exists(oeis_filename):
        with open(oeis_filename, 'w') as seq_file:
            seq_addr = "https://oeis.org/{}/b{}.txt".format(oeis_id, oeis_id[1:])
            r = requests.get(seq_addr)
            if r.status_code == 404:
                return "Error invalid OEIS ID: {}".format(oeis_id)
            seq_file.write(r.text)

    # All values are returned as strings to be handled by JS bigint on the client side
    # This will work even when values are bigger than sys.maxsize
    # JS can handle massive numbers, Python cannot
    sequence = list(np.loadtxt(oeis_filename, dtype=str, usecols=(1), max_rows=int(num_elements)))

    # If we want to handle them as ints, we need to do a trick by converting from 
    # numpy ints to python ints and then mapping and then listing
    # this is the way to do that
    # this will fail if the ints are bigger than sys.maxsize

    #sequence = list(map(int, list(np.loadtxt(oeis_filename, dtype=int, usecols=(1), max_rows=int(num_elements)))))

    response = {'id':oeis_id, 'name':'OEIS Sequence {}'.format(oeis_id), 'values': sequence}

    data = jsonify(response)

    return data

# Returns the name and cross reference of a given sequence and stores it in a temp file
# This will return an error message if sequence does not have cross reference data or valid OEIS ID
@bp.route("/api/get_metadata/<oeis_id>", methods = ["GET"])
def get_metadata(oeis_id):
    if not os.path.exists("temp"):
        os.makedirs('temp')
    meta_filename= "temp/meta{}.txt".format(oeis_id[1:])
    if not os.path.exists(meta_filename):
        with open(meta_filename, 'w') as seq_meta:
            json_addr = "https://oeis.org/search?q=id:{}&fmt=json".format(oeis_id, oeis_id[1:]) #URL for JSON format
            req = requests.get(json_addr).json()
            #pulling the results key from req
            #req contains the OEIS greeting message and sequence results in a dict
            #results contains all of the data about a given sequence
            #results is a list containing a dictionary
            #Checking for valid OEIS ID
            if req['results'] != None: #Checking for valid OEIS ID
                results = req['results'][0]
                
                if 'name' in results.keys():
                    seq_name = results['name']
                    seq_meta.write(f'{seq_name}\n')
                else:
                    seq_meta.write(f' Sequence A{oeis_id[1:]} has no name\n')
                if 'xref' in results.keys():
                    seq_xref = results['xref']
                    seq_meta.writelines(seq_xref)
                else: 
                    seq_meta.write(f'Sequence A{oeis_id[1:]} has no cross reference data.')
            else: 
                return f'ERROR invalid OEIS ID: {oeis_id}'
        
    seq_txt = list(np.loadtxt(meta_filename, dtype = str,delimiter='\n'))
    seq_dict = {'metadata': seq_txt}
    metadata = jsonify(seq_dict)
    return metadata