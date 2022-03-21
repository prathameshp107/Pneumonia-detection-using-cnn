# -*- coding: utf-8 -*-
"""
Created on Thu Jan  6 11:00:47 2022

@author: Gaurav Rathi
"""

from __future__ import division, print_function
from flask import Flask, redirect, url_for, render_template, request, flash, session
from flask_mysqldb import MySQL
from datetime import timedelta, date

# coding=utf-8
import os
import numpy as np

# Keras
from tensorflow.keras.applications.imagenet_utils import preprocess_input
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "hello" 
app.permanent_session_lifetime = timedelta(minutes=5)

app.config['MYSQL_HOST'] = "localhost"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_PASSWORD'] = ""
app.config['MYSQL_DB'] = "pneumoniadetect"
mysql = MySQL(app) 

@app.route("/")
@app.route("/index")
def home():
    if "user" in session:
        return redirect(url_for("detect"))
    elif "doctor" in session:
        return redirect(url_for("doctor"))
    else:
        return render_template("index.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/storedata", methods=['GET', 'POST'])
def storedata():
    if request.method == 'POST':
        firstName = request.form['userRegisterFirstName']
        lastName = request.form['userRegisterLastName']
        email = request.form['userRegisterEmail']
        password = request.form['userRegisterPassword']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO register (fname, lname, email, password) VALUES(%s, %s, %s, %s)", (firstName, lastName, email, password))
        mysql.connection.commit()
        cur.close()
        #flash("You are registered successfully.")
    return render_template("index.html", RegistrationValue="UserRegistrationFailed")

@app.route('/detect')  
def detect(): 
    if "user" in session:
        user = session["user"]
        return render_template("detect.html", sessionUser=user)
    else:
        return redirect(url_for("home"))  

@app.route("/checkuser", methods=['GET', 'POST'])
def checkuser():
    if request.method == "POST": 
        email = request.form['userEmail']
        password = request.form['userPassword']
        cur = mysql.connection.cursor()
        resultValue = cur.execute("SELECT * FROM register WHERE email=%s AND password=%s", (email, password))
        if resultValue > 0:
            flash("you are successfuly logged in")  
            session.permanent = True
            session["user"] = email
            return redirect(url_for('detect')) 
        else:  
            return render_template("index.html", successFailValue="UserFailed")

# Model saved with Keras model.save()
MODEL_PATH = 'chest_xray.h5'

# Load your trained model
model = load_model(MODEL_PATH)

def model_predict(img_path, model):
    img=image.load_img(path=img_path, target_size=(224,224))
    x=image.img_to_array(img)
    x=np.expand_dims(x, axis=0)
    img_data=preprocess_input(x)
    classes=model.predict(img_data)
    result=int(classes[0][0])
    if result==0:
        preds="You are Infected With Pneumonia"
    else:
        preds="You are not Infected With Pneumonia"    
    return preds

@app.route("/predict", methods=['GET', 'POST'])
def predict():
    if request.method == 'POST':
        # Get the file from post request
        f = request.files['file']
        # Save the file to ./uploads
        basepath = os.path.dirname(__file__)
        file_path = os.path.join(basepath, 'static', secure_filename(f.filename))
        f.save(file_path)
        # Make prediction
        preds = model_predict(file_path, model)
        result=preds
        cur = mysql.connection.cursor()
        user = session["user"]
        cur.execute("INSERT INTO userdata (user, imageName, imageResult, predictedOn, secondOpinion) VALUES(%s, %s, %s, %s, %s)", (user, secure_filename(f.filename), result, date.today(), 'Pending'))
        mysql.connection.commit()
        cur.close()
        return result
    return "None"
        
@app.route("/history")
def history():
    if "user" in session:
        user = session["user"]
        cur = mysql.connection.cursor()
        user = str(user)
        cur.execute("SELECT * FROM userdata WHERE user = %s", [user])
        data = cur.fetchall()
        mysql.connection.commit()
        cur.close()
        return render_template("history.html", rowsData=data)
    else:
        return redirect(url_for("home")) 

@app.route("/checkdoctor", methods=['GET', 'POST'])
def checkdoctor():
    if request.method == "POST": 
        email = request.form['doctorEmail']
        password = request.form['doctorPassword']
        if email == "doctor@gmail.com" and password == "123456":
            session.permanent = True
            session["doctor"] = "doctor"
            return redirect(url_for('doctor')) 
        else: 
            return render_template("index.html", doctorsValue="doctorFailed")
        
@app.route("/doctor")
def doctor():
    if "doctor" in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM userdata ORDER BY id DESC")
        data = cur.fetchall()
        mysql.connection.commit()
        cur.close()
        return render_template("doctor.html", rowsData=data)
    else:
        return redirect(url_for("home"))    
        
@app.route("/rightopt", methods=['GET', 'POST'])
def rightopt():
    rightid = request.form['right_id']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE userdata SET secondopinion = %s WHERE id = %s", ("Accurate Result", rightid))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for("doctor"))   
        
@app.route("/wrongopt", methods=['GET', 'POST'])
def wrongopt():
    wrongopt = request.form['wrong_id']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE userdata SET secondopinion = %s WHERE id = %s", ("Inaccurate Result", wrongopt))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for("doctor"))
        
@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("doctor", None)
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)