from flask import render_template
from . import meetups


@meetups.route('/')
def index():
    return render_template('index.html')


@meetups.route('/monthly')
def monthly():
    return render_template('index.html')


@meetups.route('/programming-night')
def programmingnight():
    return render_template('index.html')
