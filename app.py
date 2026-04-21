from flask import session, jsonify, request, render_template, redirect, url_for, flash
from portal import app, loggedin_required
from datetime import datetime, timedelta, date
import ldap
import pyodbc

@app.route('/statuschk', methods=['GET', 'POST'])
def statuschk():
    return jsonify("Site is OK")

@app.route('/', methods=['GET', 'POST'])
def index():
    rule = request.url_rule

    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        
        # Initialize variables for cleanup to avoid UnboundLocalError
        MIS_SysDev_connect = None
        MIS_SysDev_cursor = None

        try:
            # REVERTED: Use the Head Office Connection String from config
            # This ensures we query the database containing the portal_users and portal_store_users tables
            MIS_SysDev_connect = pyodbc.connect(app.config['MIS_SysDev'] + "app=" + rule.rule)
            MIS_SysDev_cursor = MIS_SysDev_connect.cursor()

            today_full = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
            conn = ldap.initialize(app.config['LDAP_PROVIDER_URL'])

            # 1. Attempt Head Office Login
            sql_ho = 'SELECT a."username", a."email", a."active", a."role", a."dept" ' \
                     'FROM dbo."portal_users" a WITH (NOLOCK) WHERE a."username"=?'
            # FIX: Ensure parameter is a tuple (username,) for pyodbc
            user = MIS_SysDev_cursor.execute(sql_ho, (username,)).fetchall()

            if user and len(user) > 0:
                if user[0][2] == 1:
                    try:
                        conn.simple_bind_s("MGROUP\\" + username, password)
                        session.update({
                            'sdr_curr_user_username': user[0][0].upper(),
                            'username': user[0][0].upper(),
                            'sdr_curr_user_role': user[0][3],
                            'sdr_loggedin': True,
                            'sdr_usertype': 'Head Office'
                        })
                        
                        print(today_full, session['sdr_usertype'], session['sdr_curr_user_username'])
                        next_page = request.args.get('next')
                        return redirect(next_page) if next_page else redirect(url_for('index', _external=True))
                    except ldap.INVALID_CREDENTIALS:
                        flash("Invalid Head Office Domain Credentials")
                        return redirect(url_for('index', _external=True))
                else:
                    flash("SDR Portal Login is deactivated!")
                    return redirect(url_for('index', _external=True))

            # 2. Fallback: Check Store Users (BCC Login)
            else:
                sql_store = 'SELECT * FROM portal_store_users WITH (NOLOCK) WHERE bcc = ?'
                # FIX: Ensure parameter is a tuple (username,)
                store = MIS_SysDev_cursor.execute(sql_store, (username,)).fetchall()

                if store and len(store) > 0:
                    domain_user = store[0][1]
                    try:
                        conn.simple_bind_s("MGROUP\\" + domain_user, password)
                        
                        today_date = date.today()
                        ante_days = store[0][4]
                        
                        session.update({
                            'sdr_curr_user_username': username.upper(),
                            'username': username.upper(),
                            'sdr_curr_user_company': store[0][3],
                            'sdr_curr_user_role': '',
                            'sdr_loggedin': True,
                            'sdr_usertype': 'Store',
                            'ante_date_int': ante_days,
                            'ante_date': (today_date - timedelta(days=ante_days))
                        })

                        print(today_full, session['sdr_usertype'], session['sdr_curr_user_username'])
                        next_page = request.args.get('next')
                        return redirect(next_page) if next_page else redirect(url_for('index', _external=True))
                    except ldap.INVALID_CREDENTIALS:
                        flash("Invalid Store Domain Credentials")
                        return redirect(url_for('index', _external=True))
                else:
                    flash("Invalid Login - Username does not exist!")
                    return redirect(url_for('index', _external=True))

        except pyodbc.Error as e:
            flash(f"Database Connectivity Error: {e}")
            return redirect(url_for('index', _external=True))
        except Exception as e:
            flash(f"System Error: {e}")
            return redirect(url_for('index', _external=True))
        finally:
            # Safe cleanup: only close if connection was established
            if MIS_SysDev_cursor:
                MIS_SysDev_cursor.close()
            if MIS_SysDev_connect:
                MIS_SysDev_connect.close()

    return render_template('home.html')

@app.route('/logout')
@loggedin_required()
def logout():
    # Securely clears all keys (including ante_date and login flags) at once
    session.clear()
    return redirect(url_for('index', _external=True))

if __name__ == '__main__':
    app.run()