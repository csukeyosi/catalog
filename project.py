import random
import string
import json
import oauth
import database_dao
from database_setup import Restaurant, MenuItem
from flask import session as login_session
from flask import (
    Flask, render_template, request, redirect, jsonify,
    url_for, flash)

app = Flask(__name__)

GOOGLE_CLIENT_SECRETS = json.loads(
    open('client_secrets.json', 'r').read())['web']

FB_CLIENT_SECRETS = json.loads(
    open('fb_client_secrets.json', 'r').read())['web']


@app.route('/login')
def showLogin():
    """ Show log in/sign up page and create anti-forgery state token. """

    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template(
        'login.html',
        STATE=state,
        FB_CLIENT_ID=FB_CLIENT_SECRETS['app_id'],
        GOOGLE_CLIENT_ID=GOOGLE_CLIENT_SECRETS['client_id'])


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    """ Connect the user using facebook. """

    response = oauth.fbconnect(FB_CLIENT_SECRETS)
    if response.status_code == 200:
        return getOutput()
    return response


@app.route('/gconnect', methods=['POST'])
def gconnect():
    """ Connect the user using google. """

    response = oauth.gconnect(GOOGLE_CLIENT_SECRETS)
    if response.status_code == 200:
        return getOutput()
    return response


def getOutput():
    """ Create the feedback when the user is logging in or signing up. """

    output = ''
    output += '<h3>Welcome, '
    output += login_session['username']
    output += '!</h3>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: '
    output += '150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;">'
    output += '</br>Redirecting...'

    createFeedback(
        200,
        "You are now logged in as %s" % login_session['username'])

    return output


@app.route('/disconnect')
def disconnect():
    """ Disconnect the user. """

    response = oauth.disconnect()
    createFeedback(response.status_code, response.data)

    return redirect(url_for('showRestaurants'))


def createFeedback(status, msg):
    """ Create a feedback for the user. """

    message = {}
    message['status'] = status
    message['msg'] = msg
    flash(message)


@app.route('/')
@app.route('/restaurant/')
def showRestaurants():
    """ Show all restaurants. """

    restaurants = database_dao.getAllRestaurants()
    return render_template(
        'restaurants.html',
        username=getUsername(),
        restaurants=restaurants)


def getUsername():
    """ Get the user's username or email, if username is not found. """

    if 'username' in login_session and login_session['username']:
        return login_session['username']

    if 'email' in login_session and login_session['email']:
        return login_session['email']

    return None


@app.route('/restaurant/new/', methods=['GET', 'POST'])
def newRestaurant():
    """ Create a restaurant. """

    if 'user_id' not in login_session or not oauth.isTokenValid():
        return redirect('/login')

    if request.method == 'POST':
        page = "showRestaurants"
        if request.form['name']:
            newRestaurant = database_dao.createRestaurant(
                request.form['name'], login_session['user_id'])
            createFeedback(
                200,
                'New Restaurant %s Successfully Created' % newRestaurant.name)
        else:
            page = "newRestaurant"
            createFeedback(400, 'Name cannot be empty')

        return redirect(url_for(page))
    else:
        return render_template('newRestaurant.html', username=getUsername())


@app.route('/restaurant/<int:restaurant_id>/edit/', methods=['GET', 'POST'])
def editRestaurant(restaurant_id):
    """ Edit a restaurant. """

    if 'user_id' not in login_session or not oauth.isTokenValid():
        return redirect('/login')

    editedRestaurant = database_dao.getRestaurant(restaurant_id)

    if login_session['user_id'] != editedRestaurant.user.id:
        createFeedback(403, 'You dont have permission to access this resource')
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))

    if request.method == 'POST':
        if request.form['name']:
            editedRestaurant.name = request.form['name']
            database_dao.update(editedRestaurant)

            createFeedback(
                200,
                'Restaurant Successfully Edited %s' % editedRestaurant.name)
            return redirect(url_for('showRestaurants'))
        else:
            createFeedback(
                400,
                'Name cannot be empty')
            return render_template(
                'editRestaurant.html',
                username=getUsername(),
                restaurant=editedRestaurant)
    else:
        return render_template(
            'editRestaurant.html',
            username=getUsername(),
            restaurant=editedRestaurant)


@app.route('/restaurant/<int:restaurant_id>/delete/', methods=['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    """ Delete a restaurant. """

    if 'user_id' not in login_session or not oauth.isTokenValid():
        return redirect('/login')

    restaurantToDelete = database_dao.getRestaurant(restaurant_id)

    if login_session['user_id'] != restaurantToDelete.user.id:
        createFeedback(403, 'You dont have permission to access this resource')
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))

    if request.method == 'POST':
        database_dao.delete(restaurantToDelete)
        createFeedback(
            200,
            '%s Successfully Deleted' % restaurantToDelete.name)

        return redirect(
            url_for(
                'showRestaurants',
                restaurant_id=restaurant_id))
    else:
        return render_template(
            'deleteRestaurant.html',
            restaurant=restaurantToDelete)


@app.route('/restaurant/<int:restaurant_id>/')
@app.route('/restaurant/<int:restaurant_id>/menu/')
def showMenu(restaurant_id):
    """ Show the restaurant's menu. """

    restaurant = database_dao.getRestaurant(restaurant_id)
    items = database_dao.getMenuItems(restaurant_id)
    can_edit = (
        'user_id' in login_session and
        restaurant.user_id == login_session['user_id'])

    return render_template(
        'menu.html',
        can_edit=can_edit,
        username=getUsername(),
        items=items,
        restaurant=restaurant,
        creator=restaurant.user)


@app.route(
    '/restaurant/<int:restaurant_id>/menu/new/',
    methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
    """ Create a new menu item. """

    if 'user_id' not in login_session or not oauth.isTokenValid():
        return redirect('/login')

    restaurant = database_dao.getRestaurant(restaurant_id)

    if login_session['user_id'] != restaurant.user.id:
        createFeedback(403, 'You dont have permission to access this resource')
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))

    if request.method == 'POST':
        newItem = MenuItem()
        if request.form['name']:
            newItem.name = request.form['name']
        if request.form['description']:
            newItem.description = request.form['description']
        if request.form['price']:
            newItem.price = request.form['price']
        if 'course' in request.form and request.form['course']:
            newItem.course = request.form['course']
        newItem.user_id = restaurant.user_id
        newItem.restaurant_id = restaurant_id

        if (
            request.form['name'] and request.form['description'] and
            request.form['price'] and
            'course' in request.form and request.form['course']):
            database_dao.update(newItem)

            createFeedback(
                200,
                'New Menu %s Item Successfully Created' % (newItem.name))
            return redirect(
                url_for(
                    'showMenu',
                    restaurant_id=restaurant_id))
        else:
            createFeedback(400, 'All Information are needed')
            return render_template(
                'newMenuItem.html',
                item=newItem,
                restaurant_id=restaurant_id)
    else:
        return render_template(
            'newMenuItem.html',
            item={},
            restaurant_id=restaurant_id)


@app.route(
    '/restaurant/<int:restaurant_id>/menu/<int:menu_id>/edit',
    methods=['GET', 'POST'])
def editMenuItem(restaurant_id, menu_id):
    """ Edit a menu item. """

    if 'user_id' not in login_session or not oauth.isTokenValid():
        return redirect('/login')

    editedItem = database_dao.getMenuItem(menu_id)
    restaurant = database_dao.getRestaurant(restaurant_id)

    if login_session['user_id'] != restaurant.user.id:
        createFeedback(403, 'You dont have permission to access this resource')
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))

    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['course']:
            editedItem.course = request.form['course']

        if (request.form['name'] and
            request.form['description'] and
            request.form['price'] and
            request.form['course']):
            database_dao.update(editedItem)

            createFeedback(200, 'Menu Item Successfully Edited')
            return redirect(url_for('showMenu', restaurant_id=restaurant_id))
        else:
            createFeedback(400, 'All Information are needed')
            return render_template(
                'newMenuItem.html',
                item=editedItem,
                restaurant_id=restaurant_id)
    else:
        return render_template(
            'newMenuItem.html',
            restaurant_id=restaurant_id,
            menu_id=menu_id,
            item=editedItem)


@app.route(
    '/restaurant/<int:restaurant_id>/menu/<int:menu_id>/delete',
    methods=['GET', 'POST'])
def deleteMenuItem(restaurant_id, menu_id):
    """ Delete a menu item. """

    if 'user_id' not in login_session or not oauth.isTokenValid():
        return redirect('/login')

    restaurant = database_dao.getRestaurant(restaurant_id)
    itemToDelete = database_dao.getMenuItem(menu_id)

    if login_session['user_id'] != restaurant.user.id:
        createFeedback(403, 'You dont have permission to access this resource')
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))

    if request.method == 'POST':
        database_dao.delete(itemToDelete)
        createFeedback(200, 'Menu Item Successfully Deleted')
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    else:
        return render_template(
            'deleteMenuItem.html',
            restaurant=restaurant,
            item=itemToDelete)


# JSON APIs to view Restaurant Information
@app.route('/restaurant/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    """ Return the restaurant's menu. """
    restaurant = database_dao.getRestaurant(restaurant_id)
    items = database_dao.getMenuItems(restaurant_id)
    return jsonify(menu_items=[i.serialize for i in items])


@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(restaurant_id, menu_id):
    """ Return the item. """
    Menu_Item = database_dao.getMenuItem(menu_id)
    return jsonify(menu_item=Menu_Item.serialize)


@app.route('/restaurant/JSON')
def restaurantsJSON():
    """ Return all restaurants. """
    restaurants = database_dao.getAllRestaurants()
    return jsonify(restaurants=[r.serialize for r in restaurants])


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
