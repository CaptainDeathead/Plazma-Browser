import flask

app = flask.Flask(__name__)

@app.route('/')
def index():
    return flask.render_template('plans.html')

@app.route('/webImages/<path:name>')
def day(name):
    return flask.send_from_directory('templates/webImages', name)

if __name__ == "__main__":
    app.run('0.0.0.0', 8080)