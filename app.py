import os
import re
import werkzeug
from flask import Flask, Response, request, render_template
from flask_mwoauth import MWOAuth
from builtins import input
from T120439 import WdCatTool

app = Flask(__name__)

from config import secret_key
app.secret_key = secret_key

@app.route("/")
def index():
    return "sup"

wikiname_regex = re.compile(r'^[a-z]+$')

def run_wdcattool():
    sourcewiki = request.args.get('from')
    if not sourcewiki or not wikiname_regex.match(sourcewiki):
        raise werkzeug.exceptions.Forbidden("illegal 'from' parameter")
    targetwiki = request.args.get('to')
    if not targetwiki or not wikiname_regex.match(targetwiki):
        raise werkzeug.exceptions.Forbidden("illegal 'to' parameter")
    try:
        wdcat = int(request.args.get('wdcat'))
    except ValueError:
        raise werkzeug.exceptions.Forbidden("illegal 'wdcat' parameter")

    wct = WdCatTool(wdcat, sourcewiki, targetwiki)
    wct.prepare()
    return wct 

@app.route("/process/json", methods=["GET", "POST"])
def json_response():
   wct = run_wdcattool()
   return Response(wct.to_json(), mimetype='application/json')
   
@app.route("/process/html", methods=["GET", "POST"])
def html_respose():
    wct = run_wdcattool()
    return render_template('result.html', **wct.to_dict())

if __name__ == "__main__":
    app.run(debug=True)
