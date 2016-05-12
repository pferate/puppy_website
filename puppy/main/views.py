from flask import render_template
from . import main


@main.route('/')
def index():
    welcome_title = "Welcome to PuPPy!"
    welcome_text = """
    We are a fun and friendly user group dedicated to proliferating a diverse
    and talented Python community in the Puget Sound region. We are devoted to
    exploring Python-based programming knowledge, embracing new and experienced
    members from all walks of life, and helping those members to achieve their
    professional goals. Please join us for a meetup, or in our social media
    discussions to get started!
    """
    return render_template('index.html', welcome_title=welcome_title, welcome_text=welcome_text)


@main.route('/about')
def about():
    return render_template('index.html')


@main.route('/contact')
def contact():
    return render_template('index.html')


@main.route('/sponsers')
def sponsers():
    return render_template('index.html')
