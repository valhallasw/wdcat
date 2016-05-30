import os
from flask import Flask
from flask_mwoauth import MWOAuth
from builtins import input

app = Flask(__name__)

from config.py import secret_key
app.secret_key = secret_key

@app.route("/")
def index():
    return "sup"

if __name__ == "__main__":
    app.run(debug=True)
