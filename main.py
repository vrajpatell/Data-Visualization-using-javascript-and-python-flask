
import os
from flask import Flask, jsonify, render_template, request, redirect
import datetime
import random
import pyodbc
app = Flask(__name__)
port = int(os.getenv("PORT", 5000))

server = 'vhpserver.database.windows.net'
database = 'vhpdatabase'
username = 'vrajpatell'
password = 'Vraj0712.'
driver= '{ODBC Driver 17 for SQL Server}'

cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1443;DATABASE='+database+';UID='+username+';PWD='+ password)

 
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('form.html')
 
#Line Chart 
@app.route('/linechart', methods = ['GET','POST'])
def linechart():   
    cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1443;DATABASE='+database+';UID='+username+';PWD='+ password)
    cursor = cnxn.cursor()
    if cnxn:
        print("if statment")
    mag1 = int(request.form['mag1'])
    mag2 = int(request.form['mag2'])    
    cursor.execute("SELECT latitude , mag from dbo.all_month where mag between '"+str(mag1)+"' and '"+str(mag2)+"' order by latitude")
    rows = cursor.fetchall()
    print(rows)
    i = 0
    v = []
    if rows != None:
        for row in rows:
            v.append({'lat':row[0],'mag':float(row[1])})
    
    print(v)
    cursor.close()
    cnxn.close()
    print("Closing Statment")
    return render_template("linechart.html", rows = v)


#Horizontal Bar Chart
@app.route('/horizontal', methods = ['GET','POST'])
def horizontal():   
    cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1443;DATABASE='+database+';UID='+username+';PWD='+ password)
    cursor = cnxn.cursor()
    if cnxn:
        print("if statment")
    mag1 = int(request.form['mag1'])
    mag2 = int(request.form['mag2'])    
    cursor.execute("SELECT mag, latitude from dbo.all_month where mag between '"+str(mag1)+"' and '"+str(mag2)+"' order by latitude")
    rows = cursor.fetchall()
    print(rows)
    i = 0
    v = []
    if rows != None:
        for row in rows:
            v.append({'mag':row[0],'lat':float(row[1])})
    
    print(v)
    cursor.close()
    cnxn.close()
    print("Closing Statment")
    return render_template("horizontalbar.html", rows = v)


#Pie Chart
@app.route('/piechart', methods = ['GET','POST'])
def piechart():   
    cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1443;DATABASE='+database+';UID='+username+';PWD='+ password)
    cursor = cnxn.cursor()
    if cnxn:
        print("if statment")
    mag1 = int(request.form['mag1'])
    mag2 = int(request.form['mag2'])    
    cursor.execute("SELECT longitude , mag from dbo.all_month where mag between '"+str(mag1)+"' and '"+str(mag2)+"' order by longitude")
    rows = cursor.fetchall()
    print(rows)
    i = 0
    v = []
    if rows != None:
        for row in rows:
            v.append({'long':row[0],'mag':float(row[1])})
    
    print(v)
    cursor.close()
    cnxn.close()
    print("Closing Statment")
    return render_template("piechart.html", rows = v)

#Scatter Plot Chart
@app.route('/scatterplot', methods = ['GET','POST'])
def scatterplot():   
    cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1443;DATABASE='+database+';UID='+username+';PWD='+ password)
    cursor = cnxn.cursor()
    if cnxn:
        print("if statment")
    mag1 = int(request.form['mag1'])
    mag2 = int(request.form['mag2'])    
    cursor.execute("SELECT latitude, longitude from dbo.all_month where mag between '"+str(mag1)+"' and '"+str(mag2)+"' ")
    rows = cursor.fetchall()
    print(rows)
    i = 0
    v = []
    if rows != None:
        for row in rows:
            v.append({'lat':row[0],'long':float(row[1])})
    
    print(v)
    cursor.close()
    cnxn.close()
    print("Closing Statment")
    return render_template("scatter.html", rows = v)
   

#Plot Between two latitude and Longitude Value   
@app.route('/plot', methods = ['GET','POST'])
def plot():    
    cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1443;DATABASE='+database+';UID='+username+';PWD='+ password)
    cursor = cnxn.cursor()
    print("connection")
    lat1 = float(request.form['lat1'])
    lat2 = float(request.form['lat2'])
    long1 = float(request.form['long1'])
    long2 = float(request.form['long2'])
        
    print(lat1)
    print(lat2)
    print(long1)
    print(long2)
       
    if lat1 > lat2:
        temp = lat1
        lat1 = lat2
        lat2 = temp
        
        
    if long1 > long2:
        temp = long1
        long1 = long2
        long2 = temp
         
    
    cursor.execute("SELECT latitude,longitude from dbo.all_month where latitude between '"+str(lat1)+"' and '"+str(lat2)+"' and longitude between '"+str(long1)+"' and '"+str(long2)+"'")
    rows = cursor.fetchall()
    result=[]
    print(rows)
    print(lat1)
    print(lat2)
    print(long1)
    print(long2)
    
    print(len(rows))
    # close database connection
    
        
    for row in rows:
        result.append({'lat': float("{0:.2f}".format(float(row[1]))), 'long' :float("{0:.2f}".format(float(row[0])))})
        
    print(result)
    
    cursor.close()
    cnxn.close()
    print("connection2")
    return render_template("scatter.html", rows = result)


if __name__ == "__main__":
	app.run(debug = True, host='0.0.0.0', port=5000, passthrough_errors=True)