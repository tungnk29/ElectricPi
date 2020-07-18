#!/usr/local/bin/python3
# -*- coding: utf-8 -*-
from flask import Flask, render_template, redirect, url_for, request, json
from module.funcs import sensor_reading, is_connected
import sqlite3 as sql
import os, re
app = Flask(__name__)

cwd = os.path.dirname(os.path.realpath(__file__))
dbpath = cwd + "/module/config.db"

def getrec(table, mode = False):
    db = sql.connect(dbpath)
    db.row_factory = sql.Row
    mouse = db.cursor()
    mouse.execute("SELECT * FROM {}".format(table))
    if not mode:
        rows = mouse.fetchall()
        res = [dict(d) for d in rows]
    else:
        rows = mouse.fetchone()
        res = dict(rows)
    db.close()
    return res

@app.route("/")
def index():
    table = getrec("config", True)
    server = table["server"]
    port = table["port"]
    token = table["token"]

    pmtab = getrec("powermeter")

    temperature = sensor_reading()
    connected = is_connected()

    return render_template("config.html", **locals())

@app.route("/srvsetup", methods=["POST"])
def srvsetup():
    db = sql.connect(dbpath)
    mouse = db.cursor()
    dictfrm = dict(request.form)
    print(dictfrm)

    domainrx = r"^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$"
    ipregex = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
    digitrx = r"^\d{2,4}$"
    tokenrx = r"^\w{16}$"

    if (re.search(domainrx, dictfrm["server"]) or re.search(ipregex, dictfrm["server"])) and re.search(digitrx, dictfrm["port"]) and re.search(tokenrx, dictfrm["token"]):
        try:
            mouse.execute("UPDATE config SET server = '{}', port = {}, token = '{}' WHERE id = 1".format(dictfrm["server"], dictfrm["port"], dictfrm["token"]))
            db.commit()
            print("Successful")
        except:
            db.rollback()
            print("Error")

    return redirect(url_for("index"))

@app.route("/save", methods=["POST"])
def save():
    db = sql.connect(dbpath)
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
    db = sql.connect(dbpath)
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
