from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem, User

# Connect to Database and create database session
engine = create_engine('sqlite:///restaurantmenuwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

def getAllRestaurants():
    """ Retrieve all restaurants. """

    return  session.query(Restaurant).order_by(asc(Restaurant.name))

def getRestaurant(restaurant_id):
    """ Retrieve the restaurant according to restaurant_id. """

    return session.query(Restaurant).filter_by(id=restaurant_id).one()

def getMenuItem(menu_item_id):
    """ Retrieve the menu item according to menu_item_id. """

    return session.query(MenuItem).filter_by(id=menu_item_id).one()

def getMenuItems(restaurant_id):
    """ Retrieve all menu items from a restaurant. """

    return session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()


def createRestaurant(name, user_id):
    """ Create a restaurant. """

    newRestaurant = Restaurant(name=name, user_id=user_id)
    session.add(newRestaurant)
    session.commit()
    return newRestaurant

def update(entity):
    """ Update an entity. """

    session.add(entity)
    session.commit()

    return entity

def delete(entity):
    """ Delete an entity. """

    session.delete(entity)
    session.commit()

def createUser(login_session):
    """ Create a new user. """

    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    """ Get the user's info. """

    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    """ Get the user's id. """

    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None