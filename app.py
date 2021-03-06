import os
import string
from flask import Flask, render_template, redirect, request, url_for
from flask_pymongo import PyMongo
from bson.objectid import ObjectId

from os import path
if path.exists("env.py"):
    import env

app = Flask(__name__)
app.config["MONGO_DBNAME"] = 'wedding-registry'
app.config["MONGO_URI"] = os.getenv('MONGO_URI', 'mongodb://localhost')

mongo = PyMongo(app)


@app.route('/')
@app.route('/homepage')
def homepage():
    return render_template('homepage.html')


# validate wishlist name and update the wishlist with new information
@app.route('/complete_wishlist', methods=['POST'])
def create_wishlist_name():
    wishlists = mongo.db.wishlists
    new_wishlist = wishlists.insert_one(request.form.to_dict())
    new_wishlist_id = new_wishlist.inserted_id
    the_wishlist = mongo.db.wishlists.find_one({"_id": ObjectId(new_wishlist_id)})
    # capitalise entered wishlist name
    the_wishlist_name = the_wishlist['wishlist_name']
    the_wishlist_name_capitalised = string.capwords(the_wishlist_name, sep = None)
    # create wishlist username - which goes into the link
    the_wishlist_username = the_wishlist_name.lower().replace(" ", "-")
    # validate the username against other wishlist usernames (must be unique, it's in the link)
    check_wishlist_usernames = wishlists.count_documents((
        {
            'wishlist_username': the_wishlist_username
         }))
    if check_wishlist_usernames == 0:
        # update the wishlist with the new information
        wishlists.update({"_id": ObjectId(new_wishlist_id)},
            {'$set':
                {
                    'wishlist_username': the_wishlist_username,
                    'wishlist_name': the_wishlist_name_capitalised
                }
            })
        return render_template('wishlist_completing.html', new_wishlist_id=new_wishlist_id,
                                wishlist=the_wishlist_name_capitalised)
    else:
        # delete this old document and return error page
        mongo.db.wishlists.remove({'_id': ObjectId(new_wishlist_id)})
        mongo.db.present.remove({"wishlist_id": ObjectId(new_wishlist_id)})
        return redirect(url_for('wishlist_username_not_available'))


# return error page that wishlist username is taken
@app.route('/wishlist_username_not_available')
def wishlist_username_not_available():
    return render_template('wishlist_username_not_available.html')


# complete the wishlist
@app.route('/<new_wishlist_id>/wishlist_created', methods=['POST'])
def complete_wishlist(new_wishlist_id):
    wishlists = mongo.db.wishlists
    the_wishlist = wishlists.find_one({'_id': ObjectId(new_wishlist_id)})
    wishlist_username = the_wishlist['wishlist_username']
    wishlists.update({"_id": ObjectId(new_wishlist_id)},
        {'$set':
            {
                'wishlist_description': request.form.get('wishlist_description'),
                'wishlist_header_image_URL': request.form.get('wishlist_header_image_URL'),
                'wishlist_wedding_date': request.form.get('wishlist_wedding_date'),
                'wishlist_wedding_location': request.form.get('wishlist_wedding_location'),
                'wishlist_theme': request.form.get('wishlist_theme')
            }
        })
    return redirect(url_for('owner_view_dynamic', wishlist_username=wishlist_username))


# owner's page where owner can add presents
# display all the presents stored with the created wishlist name in the presents collection
@app.route('/<wishlist_username>/owner')
def owner_view_dynamic(wishlist_username):
    the_wishlist = mongo.db.wishlists.find_one({'wishlist_username': wishlist_username})
    if the_wishlist:
        wishlist_username = the_wishlist['wishlist_username']
        wishlist_id = the_wishlist['_id']
        presents = mongo.db.present
        displayed_presents = presents.find({'wishlist_id_username': wishlist_username})
        categories = mongo.db.categories
        displayed_categories = categories.find()
        return render_template('owner_view.html', wishlist_id=wishlist_id,
                                the_wishlist=the_wishlist,
                                displayed_presents=displayed_presents,
                                wishlist_username=wishlist_username,
                                displayed_categories=displayed_categories)
    else:
        return redirect(url_for('homepage'))


# add presents stored with the created wishlist name in the presents collection
# link back to the owner's wishlist
@app.route('/<wishlist_username>/present_added', methods=['POST'])
def add_new_present(wishlist_username):
    presents = mongo.db.present
    new_present = presents.insert_one(request.form.to_dict())
    new_present_id = new_present.inserted_id
    presents.update({'_id': ObjectId(new_present_id)},
        {'$set':
            {
                'wishlist_id_username': wishlist_username,
                'present_availability': True,
                'present_booked_by_id': "",
                'present_booked_by_name': ""
            }
        })
    return redirect(url_for('owner_view_dynamic', wishlist_username=wishlist_username))


# delete a present from the present collection
@app.route('/<wishlist_username>/present_deleted/<present_id>')
def delete_present(wishlist_username, present_id):
    mongo.db.present.remove({'_id': ObjectId(present_id)})
    return redirect(url_for('owner_view_dynamic', wishlist_username=wishlist_username))


# edit a present of a wishlist
@app.route('/<wishlist_username>/edit_present/<present_id>')
def edit_present(wishlist_username, present_id):
    the_present = mongo.db.present.find_one({'_id': ObjectId(present_id)})
    categories = mongo.db.categories.find()
    the_wishlist = mongo.db.wishlists.find_one({"wishlist_username": wishlist_username})
    return render_template('present_editing.html', wishlist_username=wishlist_username,
                            present_id=present_id, present=the_present,
                            categories=categories,
                            the_wishlist=the_wishlist)


# update the present in the edit view
@app.route('/<wishlist_username>/update_present/<present_id>', methods=["POST"])
def update_present(wishlist_username, present_id):
    presents = mongo.db.present
    presents.update({'_id': ObjectId(present_id)},
        {'$set':
            {
                'present_title': request.form.get('present_title'),
                'present_description': request.form.get('present_description'),
                'present_header_image_URL': request.form.get('present_header_image_URL'),
                'present_quantity': request.form.get('present_quantity'),
                'present_price': request.form.get('present_price'),
                'present_category': request.form.get('present_category')
            }
        })
    return redirect(url_for('owner_view_dynamic', wishlist_username=wishlist_username))


# edit the wishlist
@app.route('/<wishlist_username>/owner/edit_wishlist')
def edit_wishlist(wishlist_username):
    the_wishlist = mongo.db.wishlists.find_one({"wishlist_username": wishlist_username})
    return render_template('wishlist_editing.html', wishlist_username=wishlist_username,
                            the_wishlist=the_wishlist)


# update the wishlist in the edit view
@app.route('/<wishlist_username>/owner/update_wishlist', methods=["POST"])
def update_wishlist(wishlist_username):
    wishlist = mongo.db.wishlists
    wishlist.update({"wishlist_username": wishlist_username},
        {'$set':
            {
                'wishlist_description': request.form.get('wishlist_description'),
                'wishlist_header_image_URL': request.form.get('wishlist_header_image_URL'),
                'wishlist_wedding_date': request.form.get('wishlist_wedding_date'),
                'wishlist_wedding_location': request.form.get('wishlist_wedding_location')
            }
        })
    return redirect(url_for('owner_view_dynamic', wishlist_username=wishlist_username))


# delete the wishlist
@app.route('/<wishlist_username>/owner/wishlist_deleted')
def delete_wishlist(wishlist_username):
    mongo.db.wishlists.remove({"wishlist_username": wishlist_username})
    mongo.db.present.remove({"wishlist_id_username": wishlist_username})
    mongo.db.username.remove({"wishlist_id_username": wishlist_username})
    return render_template('wishlist_deleted.html', wishlist_username=wishlist_username)


# go to guest page where guests can book presents
# display all the presents stored with the created wishlist name in the presents collection
@app.route('/<wishlist_username>/guest')
def guest_view_static(wishlist_username):
    the_wishlist = mongo.db.wishlists.find_one({"wishlist_username": wishlist_username})
    if the_wishlist:
        presents = mongo.db.present
        displayed_presents = presents.find({"wishlist_id_username": wishlist_username})
        return render_template('guest_view.html', wishlist_username=wishlist_username,
                                the_wishlist=the_wishlist,
                                displayed_presents=displayed_presents)
    else:
        return redirect(url_for('homepage'))


# create a guest username to book the presents
@app.route('/<wishlist_username>/guest/username_created', methods=["POST"])
def add_guest_username(wishlist_username):
    usernames = mongo.db.username
    new_username = usernames.insert_one(request.form.to_dict())
    new_username_id = new_username.inserted_id
    the_new_username = usernames.find_one({"_id": ObjectId(new_username_id)})
    # capitalise entered username name and surname
    the_user_name = the_new_username['user_name']
    the_user_surname = the_new_username['user_surname']
    the_user_name = string.capwords(the_user_name, sep = None)
    the_user_surname = string.capwords(the_user_surname, sep = None)
    # combine name and surname to create full username - which goes into the link
    the_full_user_username = the_user_name + " " + the_user_surname
    the_full_user_username_id = the_full_user_username.lower().replace(" ", "-")
    mongo.db.username.update({'_id': ObjectId(new_username_id)},
        {'$set':
            {
                'wishlist_id_username': wishlist_username,
                'full_username': the_full_user_username,
                'full_username_id': the_full_user_username_id
            }
        })
    return redirect(url_for('guest_view_dynamic', wishlist_username=wishlist_username,
                            the_full_user_username_id=the_full_user_username_id))


# go to the guest wishlist preview as a 'registered' wishlist guest
@app.route('/<wishlist_username>/guest/<the_full_user_username_id>')
def guest_view_dynamic(wishlist_username, the_full_user_username_id):
    the_wishlist = mongo.db.wishlists.find_one({'wishlist_username': wishlist_username})
    if the_wishlist:
        presents = mongo.db.present
        displayed_presents = presents.find({'wishlist_id_username': wishlist_username})
        return render_template('guest_view_username.html', wishlist_username=wishlist_username,
                                the_full_user_username_id=the_full_user_username_id,
                                displayed_presents=displayed_presents,
                                the_wishlist=the_wishlist)
    else:
        return redirect(url_for('homepage'))


# book a present with a guest name
@app.route('/<wishlist_username>/guest/<the_full_user_username_id>/<present_id>/present_booked', methods=["POST", "GET"])
def book_present(wishlist_username, the_full_user_username_id, present_id):
    usernames = mongo.db.username
    find_username_doc = usernames.find_one({'full_username_id': the_full_user_username_id})
    the_username = find_username_doc['full_username']
    presents = mongo.db.present
    presents.update({"_id": ObjectId(present_id)},
        {'$set':
            {
                'present_availability': False,
                'present_booked_by_id': the_full_user_username_id,
                'present_booked_by_name': the_username
            }
        })
    return redirect(url_for('guest_view_dynamic', wishlist_username=wishlist_username,
                            the_full_user_username_id=the_full_user_username_id))


# unbook a present
@app.route('/<wishlist_username>/guest/<the_full_user_username_id>/<present_id>/present_unbooked', methods=["POST", "GET"])
def unbook_present(wishlist_username, the_full_user_username_id, present_id):
    presents = mongo.db.present
    presents.update({"_id": ObjectId(present_id)},
        {'$set':
            {
                'present_availability': True,
                'present_booked_by_id': "",
                'present_booked_by_name': ""
            }
        })
    return redirect(url_for('guest_view_dynamic', wishlist_username=wishlist_username,
                            the_full_user_username_id=the_full_user_username_id))


if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=True)
