from flask import Flask, jsonify, render_template, request, make_response, redirect, session, url_for, flash
from flask_cors import CORS
from dotenv import load_dotenv
import mysql.connector

app = Flask(__name__)
CORS(app)
load_dotenv()


@app.route("/", methods=["GET"])
def index():
  return render_template("index.html")

@app.route("/criar-conta", methods=["GET", "POST"])
def criar_conta():
  if request.method == "GET":
    return render_template("crie_conta.html")
  elif request.method == "POST":
    return
if __name__ in "__main__":
  app.run()