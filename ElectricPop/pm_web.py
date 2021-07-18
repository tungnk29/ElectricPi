#!/usr/local/bin/python3
# -*- coding: utf-8 -*-
from flask import Flask, render_template, redirect, url_for, request, json
from redis import Redis
from module.IoTClient import Public, reds
import sqlite3 as sql
import os, re

app = Flask(__name__)
functions = Public()

# cwd = os.path.dirname(os.path.realpath(__file__))
# dbpath = cwd + "/module/config.db"
# reds = Redis(host='localhost', port=6379, db=0)

# def getrec(table, mode = False):
#     db = sql.connect(dbpath)
#     db.row_factory = sql.Row
#     mouse = db.cursor()
#     mouse.execute("SELECT * FROM {}".format(table))
#     if not mode:
#         rows = mouse.fetchall()
#         res = [dict(d) for d in rows]
#     else:
#         rows = mouse.fetchone()
#         res = dict(rows)
#     db.close()
#     return res

@app.route("/")
def index():
    server = reds.get('HOST').decode()
    port = reds.get('PORT').decode()
    token = reds.get('TOKEN').decode()
    api_url = reds.get('API_URL').decode()

    pmtab = functions.getrec("powermeter")

    temperature = functions.sensor_reading()
    connected = functions.is_connected()

    return render_template("config.html", **locals())

@app.route("/srvsetup", methods=["POST"])
def srvsetup():
    # db = sql.connect(dbpath)
    # mouse = db.cursor()
    dictfrm = dict(request.form)
    print(dictfrm)

    ipregex = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
    digitrx = r"^\d{2,4}$"
    tokenrx = r"^\w{16,}$"

    if (re.search(ipregex, dictfrm["server"])) and re.search(digitrx, dictfrm["port"]) and re.search(tokenrx, dictfrm["token"]):
        try:
            # mouse.execute("UPDATE config SET server = '{}', port = {}, token = '{}' WHERE id = 1".format(dictfrm["server"], dictfrm["port"], dictfrm["token"]))
            # db.commit()
            reds.set('HOST', dictfrm["server"])
            reds.set('PORT', dictfrm["port"])
            reds.set('TOKEN', dictfrm["token"])
            reds.set('API_URL', dictfrm["api_url"])
            print("Update server config successful!")
        except:
            # db.rollback()
            print("Error! update config fail!")

    return redirect(url_for("index"))

@app.route("/save", methods=["POST"])
def save():
    db = sql.connect(functions.DBPATH)
    db.row_factory = sql.Row
    mouse = db.cursor()

    formname = ["A", "A1", "A2", "A3", "VLL", "VLN", "V1", "V2", "V3", "V12", "V23", "V31", "PF", "PF1", "PF2", "PF3", "IDSLAVE"]
    canbe = True
    regf = dict(request.form)  # request form to dictionary

    for f in formname:
        try:
            if int(regf[f]) <= 0 and int(regf[f]) > 9999:
                canbe = False
        except:
            canbe = False

    if canbe:
        print(regf)
        try:
            if regf.get("id"):
                mouse.execute("DELETE FROM powermeter WHERE id = {}".format(regf["id"]))
                mouse.execute("INSERT INTO powermeter (id, ids, a, a1, a2, a3, vll, vln, v1, v2, v3, v12, v23, v31, pf, pf1, pf2, pf3) VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})".format(regf["id"], regf["IDSLAVE"], regf["A"], regf["A1"], regf["A2"], regf["A3"], regf["VLL"], regf["VLN"], regf["V1"], regf["V2"], regf["V3"], regf["V12"], regf["V23"], regf["V31"], regf["PF"], regf["PF1"], regf["PF2"], regf["PF3"]))
            else:
            	mouse.execute("INSERT INTO powermeter (ids, a, a1, a2, a3, vll, vln, v1, v2, v3, v12, v23, v31, pf, pf1, pf2, pf3) VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})".format(regf["IDSLAVE"], regf["A"], regf["A1"], regf["A2"], regf["A3"], regf["VLL"], regf["VLN"], regf["V1"], regf["V2"], regf["V3"], regf["V12"], regf["V23"], regf["V31"], regf["PF"], regf["PF1"], regf["PF2"], regf["PF3"]))
            db.commit()
            return json.dumps({'status': True})
        except:
            db.rollback()
            print("Error :(")
        finally:
            db.close()

    return json.dumps({'status': False})

@app.route("/delete", methods=["POST"])
def delete():
    db = sql.connect(functions.DBPATH)
    mouse = db.cursor()

    try:
        mouse.execute("DELETE FROM powermeter WHERE id = {}".format(request.form["id"]))
        db.commit()
        return json.dumps({'status': True, 'delete': 'Ok'})
    except:
        db.rollback()
        print("Error :(")
    finally:
        db.close()

    return json.dumps({'status': True, 'delete': 'Ok'})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
