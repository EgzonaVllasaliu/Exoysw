from flask import Flask, render_template, request, redirect, flash, session
from mysqlconnection import connectToMySQL
from flask_bcrypt import Bcrypt
import re
from datetime import datetime
# import os

# print(os.urandom(24).hex())

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = '26802dffaa511c660dcefc6bf253b2c611f18a2091824f17'

EMAIL_REGEX = re.compile(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)')
schema = "dojo_project"

@app.route('/')
def landing():
   return render_template('logreg.html')

@app.route('/register' , methods=["POST"])
def create_user():
    isValid = True
    
    if(len(request.form['fname']) < 2 and not request.form['fname'].isalpha()):
        isValid = False
        flash("First name must be at least 2 characters and contain only letters!")
    if(len(request.form['lname']) < 2 ):
        isValid = False
        flash("Last name must be at least 2 characters")
    if (len(request.form['email']) < 2 and not not EMAIL_REGEX.match(request.form['email'])):
        isValid = False
        flash("Please enter a valid email!")
    if (len(request.form['password']) < 8):
        isValid = False
        flash("Must be at least 8 characters!")
    if(request.form['password'] != request.form['cpassword']):
        isValid = False
        flash("Password doesn't match!")
        
    mysql = connectToMySQL(schema)
    
    validate_email_query = 'SELECT user_id FROM users WHERE email=%(email)s;'
    form_data = {
        'email': request.form['email']
    }
    existing_users = mysql.query_db(validate_email_query, form_data)

    if existing_users:
        flash("Email already in use")
        isValid = False     
    if isValid:
        mysql = connectToMySQL(schema)
        query = "INSERT INTO users(first_name, last_name, email, password, created_at, updated_at) VALUES (%(fname)s,%(lname)s,%(email)s,%(password)s, NOW(), NOW())"
        
        data = {
            "fname" : request.form['fname'],
            "lname" : request.form['lname'],
            "email" : request.form['email'],
            "password" : bcrypt.generate_password_hash(request.form['password'])
        }     
        user_id = mysql.query_db(query, data)
        
        session['user_id'] = user_id
        session['first_name'] = request.form['fname']
        return redirect('/home')
    else:
        return redirect('/')    
    
@app.route('/login', methods=["POST"])
def login():
    isValid = True
    
    if len(request.form['email']) < 1: 
        isValid = False
        flash("Please enter your email!")
    if not EMAIL_REGEX.match(request.form['email']):
        isValid = False
        flash("Please enter a valid email!")    
    if len(request.form['password']) < 1: 
        isValid = False
        flash("Please enter your password!")

        
    if not isValid:
        return redirect('/')        
    else:
        mysql = connectToMySQL(schema)
        query = "SELECT * FROM users WHERE users.email = %(email)s"
        data = {
            'email': request.form['email']
        }
        user = mysql.query_db(query, data)
        if user:
            hashed_password = user[0]['password']
            if bcrypt.check_password_hash(hashed_password, request.form['password']):
                session['user_id'] = user[0]['user_id']
                session['first_name'] = user[0]['first_name']
                return redirect("/home")
            else:
                flash("Password is invalid")
                return redirect("/")
        else:
            flash("Please use a valid email address")
            return redirect("/")  

@app.route('/home')
def home():
    
    return render_template('home.html')  
   

   
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)