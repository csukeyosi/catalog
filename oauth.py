from flask import request
from flask import session as login_session

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

import database_dao

GOOGLE = 'google'
FACEBOOK = 'facebook'


def fbconnect(client_secrets):
    """ Connect the user using facebook. """

    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = client_secrets['app_id']
    app_secret = client_secrets['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    print result

    # Use token to get user info from API
    token = json.loads(result.split("&")[0])
    url = 'https://graph.facebook.com/v2.8/me?access_token=%s&fields=name,id,email' % token['access_token']

    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    data = json.loads(result)
    login_session['provider'] = FACEBOOK
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout, let's strip out the information before the equals sign in our token
    login_session['access_token'] = token['access_token']

    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?access_token=%s&redirect=0&height=200&width=200' % token['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    print '\n\n\n'
    print result
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = database_dao.getUserID(login_session['email'])
    if not user_id:
        user_id = database_dao.createUser(login_session)
    login_session['user_id'] = user_id

    response = make_response(json.dumps('Login Successful!'), 200)
    response.headers['Content-Type'] = 'application/json'
    return response


def gconnect(client_secrets):
    """ Connect the user using google. """

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
    except FlowExchangeError, error:
        print error
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
    if result['issued_to'] != client_secrets['client_id']:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
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

    login_session['provider'] = GOOGLE
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # See if a user exists, if it doesn't make a new one
    user_id = database_dao.getUserID(data['email'])
    if  user_id is None:
        user_id = database_dao.createUser(login_session)
    login_session['user_id'] = user_id

    response = make_response(json.dumps('Login Successful!'), 200)
    response.headers['Content-Type'] = 'application/json'
    return response


def disconnect():
    """ Disconnect the user. """

    if 'access_token' not in login_session or login_session['access_token'] is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = login_session['access_token']
    h = httplib2.Http()
    provider = login_session['provider']

    if provider == FACEBOOK:
        facebook_id = login_session['facebook_id']
        url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id, access_token)
        result = h.request(url, 'DELETE')[0]
    else:
        url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
        result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        response = make_response(json.dumps('User was disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'

    else:
        response = make_response(json.dumps(result.reason), result.status)
        response.headers['Content-Type'] = 'application/json'

    # Reset the user's sesson.
    login_session.clear()

    return response