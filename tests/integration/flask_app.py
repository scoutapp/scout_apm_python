# coding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "Welcome home."


@app.route("/hello/")
def hello():
    return "Hello World!"


@app.route("/crash/")
def crash():
    raise ValueError("BØØM!")  # non-ASCII
