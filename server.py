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

@app.route("/home")
def home():
    if 'user_id' not in session:
        return redirect("/")  
    
    mysql = connectToMySQL(schema)
    query = "SELECT * FROM users WHERE user_id = %(id)s"
    data = {
        "id" : session['user_id']
    } 
    user = mysql.query_db(query, data)
    
    query = "SELECT * FROM users WHERE user_id <> %(id)s ORDER BY last_name ASC"
    mysql = connectToMySQL(schema)
    data = {
        'id': session['user_id']
    }
    users = mysql.query_db(query, data)

    mysql = connectToMySQL(schema)
    query = "SELECT user_being_followed FROM followed_users WHERE user_following = %(id)s"
    data = {
        'id': session['user_id']
    }
    followed_users = [user['user_being_followed'] for user in mysql.query_db(query, data)]
    
    mysql = connectToMySQL(schema)
    query = "SELECT tweets.user_id, tweets.tweet_id as tweet_id, users.first_name,users.last_name,  tweets.content, tweets.created_at, tweets.content, COUNT(liked_tweets.tweet_id) as times_liked FROM liked_tweets RIGHT JOIN tweets ON tweets.tweet_id = liked_tweets.tweet_id JOIN users ON tweets.user_id = users.user_id GROUP BY tweets.tweet_id ORDER BY tweets.created_at DESC;"
    tweets = mysql.query_db(query)
    
    mysql = connectToMySQL(schema)
    query = "SELECT * FROM liked_tweets WHERE user_id = %(user_id)s"
    data = {
        'user_id': session['user_id']
    }
    liked_tweets = [tweet['tweet_id'] for tweet in mysql.query_db(query, data)]
    
    for tweet in tweets:
        time_since_posted = datetime.now() - tweet['created_at']
        days = time_since_posted.days
        hours = time_since_posted.seconds//3600 
        minutes = (time_since_posted.seconds//60)%60
        if tweet['tweet_id'] in liked_tweets:
            tweet['already_liked'] = True
        else:
            tweet['already_liked'] = False        

        tweet['time_since_posted'] = (days, hours, minutes)
        
    return render_template('home.html',user=user[0], tweets=tweets, users = users, followed_users = followed_users)
   
@app.route("/tweets/create", methods=['POST'])
def save_tweet():
    if 'user_id' not in session:
        return redirect("/")
        
    is_valid = True
    if len(request.form['content']) < 1:
        is_valid = False
        flash('Tweet cannot be blank')
    if len(request.form['content']) >= 256:
        is_valid = False
        flash('Tweet cannot be more than 255 characters')
    
    if is_valid:
        mysql = connectToMySQL(schema)
        query = "INSERT INTO tweets (content, created_at, updated_at, user_id) VALUES (%(cont)s, NOW(), NOW(), %(id)s)"
        data = {
            'cont': request.form['content'],
            'id': session['user_id'],
        }
        tweet = mysql.query_db(query, data)
    
    return redirect("/home")

@app.route("/tweets/<tweet_id>/add_like")
def like_tweet(tweet_id):
    query = "INSERT INTO liked_tweets (user_id, tweet_id) VALUES (%(user_id)s, %(tweet_id)s)"
    data = {
        'user_id': session['user_id'],
        'tweet_id': tweet_id
    }
    mysql = connectToMySQL(schema)
    mysql.query_db(query, data)
    return redirect("/home")

@app.route("/tweets/<tweet_id>/unlike")
def unlike_tweet(tweet_id):
    query = "DELETE FROM liked_tweets WHERE user_id = %(user_id)s AND tweet_id = %(tweet_id)s"
    data = {
        'user_id': session['user_id'],
        'tweet_id': tweet_id
    }
    mysql = connectToMySQL(schema)
    mysql.query_db(query, data)
    return redirect("/home")

@app.route("/tweets/<tweet_id>/delete")
def delete_tweet(tweet_id):

    query = "DELETE FROM liked_tweets WHERE tweet_id = %(tweet_id)s"
    data = {
        'tweet_id': tweet_id
    }
    mysql = connectToMySQL(schema)
    mysql.query_db(query, data)

    query = "DELETE FROM tweets WHERE tweet_id = %(tweet_id)s"
    mysql = connectToMySQL(schema)
    mysql.query_db(query, data)
    return redirect("/home")

@app.route("/follow/<user_id>")
def follow_user(user_id):
    query = "INSERT INTO followed_users (user_following, user_being_followed) VALUES (%(uid)s, %(uid2)s)"
    mysql = connectToMySQL(schema)
    data = {
        'uid': session['user_id'],
        'uid2': user_id
    }
    mysql.query_db(query, data)
    return redirect("/home")

@app.route("/unfollow/<user_id>")
def unfollow_user(user_id):
    query = "DELETE FROM followed_users WHERE user_following = %(uid)s AND user_being_followed = %(uid2)s"
    data = {
        'uid': session['user_id'],
        'uid2': int(user_id)
    }
    mysql = connectToMySQL(schema)
    mysql.query_db(query, data)
    return redirect("/home")

@app.route("/usersearch", methods= ["GET"])
def search():
    mysql = connectToMySQL(schema)
    query = "SELECT users.first_name FROM users WHERE users.first_name LIKE %%(name)s;"
    data = {
        "name" : request.args.get('first_name')
    }
    results = mysql.query_db(query, data)
    print(results)
    return render_template("usersearch.html", users = results)

# Profile 

@app.route('/profile/<user_id>')
def profile(user_id):
    if 'user_id' not in session:
        return redirect("/")  
    
    mysql = connectToMySQL(schema)
    query = "SELECT * FROM users WHERE user_id = %(id)s"
    data = {
        "id" : session['user_id']
    } 
    user = mysql.query_db(query, data)
    
    mysql = connectToMySQL(schema)
    query = "SELECT tweets.user_id, tweets.tweet_id as tweet_id, users.first_name,users.last_name,tweets.content, tweets.created_at, tweets.content, COUNT(liked_tweets.tweet_id) as times_liked FROM liked_tweets RIGHT JOIN tweets ON tweets.tweet_id = liked_tweets.tweet_id JOIN users ON tweets.user_id = users.user_id where users.user_id = %(user_id)s GROUP BY tweets.tweet_id ORDER BY tweets.created_at DESC"
    data = {
        'user_id': user_id
    }
    tweets = mysql.query_db(query,data)
    
    mysql = connectToMySQL(schema)
    query = "SELECT * FROM liked_tweets WHERE user_id = %(user_id)s"
    data = {
        'user_id': session['user_id']
    }
    liked_tweets = [tweet['tweet_id'] for tweet in mysql.query_db(query, data)]
    
    mysql = connectToMySQL(schema)
    query = "SELECT user_being_followed FROM followed_users WHERE user_following = %(id)s"
    data = {
        'id': session['user_id']
    }
    followed_users = [user['user_being_followed'] for user in mysql.query_db(query, data)]
    
    for tweet in tweets:
        time_since_posted = datetime.now() - tweet['created_at']
        days = time_since_posted.days
        hours = time_since_posted.seconds//3600 
        minutes = (time_since_posted.seconds//60)%60
        if tweet['tweet_id'] in liked_tweets:
            tweet['already_liked'] = True
        else:
            tweet['already_liked'] = False        

        tweet['time_since_posted'] = (days, hours, minutes)
        
    query = "SELECT followed_users.user_following, count(being_followed.user_id) as following FROM followed_users LEFT JOIN users on followed_users.user_following = users.user_id LEFT JOIN users as being_followed on followed_users.user_being_followed = being_followed.user_id WHERE followed_users.user_following =  %(uid)s"
    data = {
        'uid': user_id
    }
    mysql = connectToMySQL(schema)
    following = mysql.query_db(query, data)
    
    query = "SELECT followed_users.user_being_followed, count(userFollowing.user_id) as followers FROM followed_users LEFT JOIN users on followed_users.user_being_followed = users.user_id LEFT JOIN users as userFollowing on followed_users.user_following = userFollowing.user_id WHERE followed_users.user_being_followed  = %(uid)s"
    data = {
        'uid': user_id
    }
    mysql = connectToMySQL(schema)
    followers = mysql.query_db(query, data)
    print(following)
    print(followers)
    return render_template("profile.html", user=user[0] ,tweets=tweets, followers=followers[0], following=following[0])

@app.route("/tweetsP/<tweet_id>/add_like")
def like_tweetP(tweet_id):
    query = "INSERT INTO liked_tweets (user_id, tweet_id) VALUES (%(user_id)s, %(tweet_id)s)"
    data = {
        'user_id': session['user_id'],
        'tweet_id': tweet_id
    }
    mysql = connectToMySQL(schema)
    mysql.query_db(query, data)
    return redirect("/profile/{}".format(user_id)) 

@app.route("/tweetsP/<tweet_id>/unlike")
def unlike_tweetP(tweet_id):
    query = "DELETE FROM liked_tweets WHERE user_id = %(user_id)s AND tweet_id = %(tweet_id)s"
    data = {
        'user_id': session['user_id'],
        'tweet_id': tweet_id
    }
    mysql = connectToMySQL(schema)
    mysql.query_db(query, data)
    return redirect("/profile/{}".format(user_id)) 

@app.route("/tweetsP/<tweet_id>/delete")
def delete_tweetP(tweet_id):
    if 'user_id' not in session:
        return redirect("/")  
    
    query = "DELETE FROM liked_tweets WHERE tweet_id = %(tweet_id)s"
    data = {
        'tweet_id': tweet_id
    }
    mysql = connectToMySQL(schema)
    mysql.query_db(query, data)

    query = "DELETE FROM tweets WHERE tweet_id = %(tweet_id)s"
    mysql = connectToMySQL(schema)
    mysql.query_db(query, data)
    return redirect("/profile/{}".format(user_id)) 


@app.route("/followP/<user_id>")
def follow_userP(user_id):
    query = "INSERT INTO followed_users (user_following, user_being_followed) VALUES (%(uid)s, %(uid2)s)"
    mysql = connectToMySQL(schema)
    data = {
        'uid': session['user_id'],
        'uid2': user_id
    }
    mysql.query_db(query, data)
    return redirect("/profile/{}".format(user_id)) 
    

@app.route("/unfollowP/<user_id>")
def unfollow_userP(user_id):
    query = "DELETE FROM followed_users WHERE user_following = %(uid)s AND user_being_followed = %(uid2)s"
    data = {
        'uid': session['user_id'],
        'uid2': int(user_id)
    }
    mysql = connectToMySQL(schema)
    mysql.query_db(query, data)
    return redirect("/profile/{}".format(user_id)) 


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)