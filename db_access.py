import sqlite3
import datetime, hashlib
from flask import app, g
from chirpr import app


def db_exec(*args, commit=False):
    conn = get_db()
    if commit == True:
        conn.execute(*args)
        conn.commit()
        conn.close()
    else:
        return conn.execute(*args)


def hash_ps(text):
    return hashlib.sha224(text.encode('utf-8')).hexdigest()


def add_chirp(text, uID):
    db_exec('INSERT INTO chirp (body, user_id, datetime) VALUES (?,?,?)', (text, uID, str(datetime.datetime.utcnow())), commit=True)


def edit_bio(uID, bio):
    if len(bio) in range(0,180):
        db_exec('UPDATE user SET bio=? WHERE id=?', (bio,uID), commit=True)
        return True
    return False


def get_all_chirps(uid):
    return db_exec('SELECT c.id, c.body, c.datetime, u.handle FROM chirp c, user u, followers f WHERE f.follower_id = ? AND c.user_id = u.id AND c.user_id = f.leader_id ORDER BY c.id DESC', (uid,)).fetchall()


def get_chirps(uid):
    return db_exec('SELECT c.id, c.body, c.datetime, u.handle FROM chirp c, user u WHERE c.user_id = u.id AND c.user_id=? ORDER BY c.id DESC', (uid,)).fetchmany(100)


def delete_chirp(chirp_id, user_id):
    db_exec('DELETE FROM chirp WHERE id = :id AND user_id = :uid', {'id': chirp_id, 'uid':user_id}, commit=True)


def get_all_users():
    return db_exec('SELECT id, handle, admin FROM user').fetchall()


def follower_of(leader_id, follower_id):
    return db_exec('SELECT * FROM followers WHERE leader_id=:lid AND follower_id=:fid', {'lid':leader_id, 'fid':follower_id}).fetchone()


def follow(leader_id, follower_id):
    if follower_of(leader_id, follower_id) is None:
        db_exec('INSERT INTO followers VALUES (?,?)', (leader_id, follower_id), commit=True)
        return True
    return False


def followers(uid):
    return db_exec('SELECT leader_id FROM followers WHERE follower_id=?', (uid,)).fetchall()


def user_data(leader_id):
    followers = {'count_followers':0}
    f = 'count_followers'
    for i in db_exec('SELECT leader_id, follower_id FROM followers WHERE leader_id=?', (leader_id,)):
        if f in followers:
            followers[f] += 1
    followers['bio'] = db_exec('SELECT bio FROM user WHERE id=?', (leader_id,)).fetchone()[0]
    return followers


def user_exists(uid):
    exists = db_exec('SELECT handle FROM user WHERE id=:id', {'id':uid}).fetchone()
    return False if exists is None else True

def get_user(uid):
    user = db_exec('SELECT handle FROM user WHERE id=:id', {'id':uid}).fetchone()
    return user[0] if user is not None else None
    

def get_id(user):
    ID = db_exec('SELECT id FROM user WHERE handle=:user', {'user':user}).fetchone()
    return ID[0] if ID is not None else None


def get_users_like(like_handle):
    like_handle = '%' + like_handle + '%'
    return list(db_exec('SELECT * FROM user WHERE handle LIKE :like_handle', {'like_handle':like_handle}))
   
    
def get_user_by_handle_and_password(handle, password):
    password = hash_ps(password)
    return db_exec('SELECT id FROM user WHERE handle=:handle AND password=:password', {'handle':handle, 'password':password}).fetchone()
    
    
def delete_user(user_id):
    db_exec('DELETE FROM user WHERE id = :id', {'id': user_id}, commit=True)


def add_user(handle, password):
    password = hash_ps(password)
    conn = get_db()
    conn.execute('INSERT INTO user (handle, password, admin, bio) values (:handle, :password, :admin, :bio)', {'handle': handle, 'password':password, 'admin': 0, 'bio':''})
    conn.commit()
    hid = get_id(handle)
    conn.execute('INSERT INTO followers VALUES (?,?)',(hid,hid))
    conn.commit()
    
def create_account(handle, password):
    res = db_exec('SELECT * FROM user WHERE handle=:handle', {'handle':handle})
    if list(res):
        state = False
    else:
        add_user(handle, password)
        state = True
    return state


def get_db():
    if not hasattr(g, 'chirpr.db'):
        g.conn = connect_db()
    return g.conn


def connect_db():
    conn = sqlite3.connect('data/chirpr.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'conn'):
        g.conn.close()
