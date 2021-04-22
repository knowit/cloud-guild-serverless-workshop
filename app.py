import boto3
import os

from flask import Flask, jsonify, make_response, request
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime
from uuid import uuid4
from contextlib import closing
from tempfile import gettempdir

BUCKET_NAME = os.environ["audioBucket"]

polly = boto3.client("polly")
s3 = boto3.client("s3")

app = Flask(__name__)


@app.route("/")
def hello_from_root():
    return jsonify(message='Hello from root!')


@app.route("/hello")
def hello():
    return jsonify(message='Hello from path!')


@app.route("/polly", methods=["POST"])
def do_text_to_speech():
    o = request.get_json(force=True)
    if 'polly' in o:
        txt = o['polly']
        try:
            print(polly)
            response = polly.synthesize_speech(Text=txt, OutputFormat="ogg_vorbis", VoiceId="Joanna")
        except (BotoCoreError, ClientError) as error:
            return jsonify(f"Error when synthesizing text: {error}")
        if "AudioStream" in response:
            output = os.path.join(gettempdir(), "speech.ogg")
            with closing(response["AudioStream"]) as stream:
                try:
                    with open(output, "wb") as f:
                        f.write(stream.read())
                except IOError as error:
                    return jsonify(f"Error when writing to tempfile: {error}")
            key = f"{datetime.now().isoformat()}_{uuid4()}.ogg"
            s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=open(output, "r+b"))
            return jsonify(f"You may download your TTS from: s3://{BUCKET_NAME}/{key}")
        else:
            return jsonify(f"No AudioStream in response from Polly!")
    else:
        return jsonify(f"Illegal polly object: {o}")


@app.errorhandler(404)
def resource_not_found(e):
    return make_response(jsonify(error='Not found!'), 404)
