from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################

# Service health
@app.route("/health")
def health():
    
    return jsonify(dict(status="OK")), 200

# Song count
@app.route("/count")
def count():
    """return length of data"""
    count = db.songs.count_documents({})

    return {"count": count}, 200

# Song list
@app.route("/song")
def songs():
    songs_list = list(db.songs.find({}))
    print(songs_list[0])

    return {"songs": parse_json(songs_list)}, 200

# Single song
@app.route("/song/<int:id>")
def get_song_by_id(id):
    song = db.songs.find_one({"id": id})
    if not song:
        return {"message": f"song with id {id} not found"}, 404

    return parse_json(song), 200

# Create new song
@app.route("/song", methods=["POST"])
def create_song():

    song_in = request.json
    print(song_in["id"])

    # If a song with the id already exists, send an HTTP code of 302 back to the user 
    song = db.songs.find_one({"id": song_in["id"]})
    if song:
        return {
            "Message": f"song with id {song_in['id']} already present"
        }, 302
    insert_id: InsertOneResult = db.songs.insert_one(song_in)

    return {"inserted id": parse_json(insert_id.inserted_id)}, 201

# Update song
@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):

    song_changes = request.json
    song = db.songs.find_one({"id": id})

    # If the song does not exist, you will send back a status of 404
    if song == None:
        return {"message": "song not found"}, 404

    # If the song exists, you will update it 
    updated_data = {"$set": song_changes}
    result = db.songs.update_one({"id": id}, updated_data)
    
    if result.modified_count == 0:
        return {"message": "song found, but nothing updated"}, 200
    else:
        return parse_json(db.songs.find_one({"id": id})), 201
