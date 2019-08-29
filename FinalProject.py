from flask import (
    Flask, 
    render_template, 
    request, 
    redirect, 
    url_for, 
    flash, 
    jsonify
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem, User

from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

CLIENT_ID = \
json.loads(open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu App"

app = Flask(__name__)

engine = create_engine('sqlite:///restaurantmenuwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def createUser(login_session):
    session = DBSession()
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    session = DBSession()
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    session = DBSession()
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print ("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data.get('name', '')
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += """ "style = "width: 300px; height: 300px;
    border-radius: 150px;-webkit-border-radius: 150px;
    -moz-border-radius: 150px;"> """
    flash("you are now logged in as %s" % login_session['username'])
    print ("done!")
    return output


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print ('Access Token is None')
        response = make_response(json.dumps('Current user not connected'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print ('In gdisconnect access token is %s', access_token)
    print ('User name is: ')
    print (login_session['username'])
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' \
                % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print ('result is ')
    print (result)
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/restaurants/JSON')
def restaurantJSON():
    session = DBSession()
    restaurants = session.query(Restaurant).all()
    return jsonify(Restaurants=[i.serialize for i in restaurants])


@app.route('/restaurants/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    session = DBSession()
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id).all()
    return jsonify(MenuItems=[i.serialize for i in items])


@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(restaurant_id,menu_id):
    session = DBSession()
    item = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(MenuItem=item.serialize)


@app.route('/')
@app.route('/restaurants/')
def restaurants():
    session = DBSession()
    restaurants = session.query(Restaurant).all()
    return render_template('restaurants.html', restaurants=restaurants)


@app.route('/restaurants/<int:restaurant_id>/menu')
def restaurantMenu(restaurant_id):
    """
   This is a function to add new menu item
    Args:
        restaurant_id (data type: Integer): 
                    the restaurant id that menu belongs to 
    Returns:
     restaurant menu page
    """
    session = DBSession()
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    creator = getUserInfo(restaurant.user_id)
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id)
    if items is None:
        return "You currently have no menu items"
    else:
        return render_template('menu.html', restaurant=restaurant, 
                        items=items, creator=creator)


@app.route('/restaurant/new', methods=['GET','POST'])
def newRestaurant():
    """
   This is a function to add new menu item
    Returns:
        if the restaurant is created successfully, 
            return to restaurant page and show message:New restqurant created!
        else return to restaurant page and show no message.
    """
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newRestaurant = Restaurant(name=request.form['name'], 
                    user_id=login_session['user_id'])
        session.add(newRestaurant)
        session.commit()
        flash('New restaurant %s created!' % newRestaurant.name)
        return redirect(url_for('restaurants'))
    else:
        return render_template('newRestaurant.html')


@app.route('/restaurant/<int:restaurant_id>/menu/new/', methods=['GET','POST'])
def newMenuItem(restaurant_id):
    """
   This is a function to add new menu item
    Args:
        restaurant_id (data type: Integer): 
                    the restaurant id that menu belongs to 
    Returns:
        if the menu item is created successfully, 
            return to restaurant menu page and show message:New menu item created!
        else return to restaurant menu page and show no message.
    """
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newItem = MenuItem(name=request.form['name'], 
                            course=request.form['course'], 
                            description=request.form['description'], 
                            price=request.form['price'], 
                            restaurant_id=restaurant_id, 
                            user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash("New menu item created!")
        return redirect(url_for('restaurantMenu', restaurant_id = restaurant_id))
    else:
        return render_template('newmenuitem.html', restaurant_id = restaurant_id)


@app.route('/restaurant/<int:restaurant_id>/edit/', methods=['GET','POST'])
def editRestaurant(restaurant_id):
    """
   This is a function to add new menu item
    Args:
        restaurant_id (data type: Integer): 
                    the restaurant id 
    Returns:
        if the restaurant infomation is edited successfully, 
            return to restaurant page and show message: Restaurant was edited!
        else return to restaurant page and show no message.
    """
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    editedRes = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if editedRes.user_id == login_session['user_id']:
        if request.method == 'POST':
            if request.form['name']:
                editedRes.name = request.form['name']
            session.add(editedRes)
            session.commit()
            flash("Restaurant was edited!")
            return redirect(url_for('restaurants'))
        else:
            return render_template('editRestaurant.html', restaurant=editedRes)
    else: 
        flash("You are not allowed to edit this restaurant.")
        return redirect(url_for('restaurants'))


@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/edit/', 
        methods=['GET','POST'])
def editMenuItem(restaurant_id, menu_id):
    """
   This is a function to add new menu item
    Args:
        restaurant_id (data type: Integer): 
                    the restaurant id that menu belongs to 
        menu-id(data type: Integer):
                    the menu id
    Returns:
        if the menu item is edited successfully, 
            return to restaurant menu page and show message:menu item was edited!
        else return to restaurant menu page and show no message.
    """
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    if editedItem.user_id == login_session['user_id']:
        if request.method == 'POST':
            if request.form['name']:
                editedItem.name=request.form['name']
            if request.form['description']:
                editedItem.description=request.form['description']
            if request.form['price']:
                editedItem.price = request.form['price']
            if request.form['course']:
                editedItem.course = request.form['course']
            session.add(editedItem)
            session.commit()
            flash("Menu item was edited!")
            return redirect(url_for('restaurantMenu', 
                        restaurant_id=restaurant_id))
        else:
            return render_template('editmenuitem.html', 
                                    restaurant_id=restaurant_id, 
                                    menu_id=menu_id, item=editedItem)
    else:
        flash("You are not allowed to edit this menu item.")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))


@app.route('/restaurant/<int:restaurant_id>/delete/', methods=['GET','POST'])
def deleteRestaurant(restaurant_id):
    """
   This is a function to add new menu item
    Args:
        restaurant_id (data type: Integer): 
                    the restaurant id
    Returns:
        if the restaurant is deleted successfully, 
            return to restaurant page and show message:Restaurant was deleted!
        else return to restaurant page and show no message.
    """
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    deletedRes = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if deletedRes.user_id == login_session['user_id']:
        if request.method == 'POST':
            session.delete(deletedRes)
            session.commit()
            flash("Restaurant was deleted!")
            return redirect(url_for('restaurants'))
        else:
            return render_template('deleteRestaurant.html', 
                        restaurant=deletedRes)
    else:
        flash("You are not allowed to delete this restaurant.")
        return redirect(url_for('restaurants'))


@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/delete/', 
            methods=['GET','POST'])
def deleteMenuItem(restaurant_id, menu_id):
    """
   This is a function to add new menu item
    Args:
        restaurant_id (data type: Integer): 
                    the restaurant id that menu belongs to
        menu_id(data type: Integer):
                    the menu id 
    Returns:
        if the menu item is deleted successfully, 
            return to restaurant menu page and show message:menu item was deleted!
        else return to restaurant menu page and show no message.
    """
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    deletedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    if deletedItem.user_id == login_session['user_id']:
        if request.method == 'POST':
            session.delete(deletedItem)
            session.commit()
            flash("Menu item was deleted!")
            return redirect(url_for('restaurantMenu', 
                            restaurant_id=restaurant_id))
        else:
            return render_template('deletemenuitem.html', item=deletedItem)
    else:
        flash("You are not allowed to delete this menu item.")
        return redirect(url_for('restaurantMenu', 
                                restaurant_id=restaurant_id))

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host = '172.26.6.164', port = 80)