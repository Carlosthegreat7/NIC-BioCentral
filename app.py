# RR 06-10-2025
from flask import session, jsonify, request, render_template, redirect, url_for, flash
from portal import app, loggedin_required
# from portal.functions import generate_earliest_missing_date
# from waitress import serve
from datetime import datetime
from datetime import timedelta
from datetime import date
import os
import ldap
import pyodbc



@app.route('/statuschk', methods=['GET', 'POST'])
def statuschk():
	d = "Site is OK"
	return jsonify(d)



@app.route('/', methods=['GET', 'POST'])
def index():
	# print("index", session['sdr_loggedin'])
	rule = request.url_rule

	if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
		username = request.form['username']
		password = request.form['password']
		print("username", username)

		conn = ldap.initialize(app.config['LDAP_PROVIDER_URL'])


		today = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

		try:
			MIS_SysDev_connect	= pyodbc.connect(app.config['MIS_SysDev']+"app="+rule.rule)
			MIS_SysDev_cursor	= MIS_SysDev_connect.cursor()

			sql_comm_strng = 'SELECT a."username", a."email", a."active", a."role", a."dept" ' \
    						'FROM dbo."portal_users" a with (NOLOCK) where a."username"=? '
			user = MIS_SysDev_cursor.execute(sql_comm_strng, (username) ).fetchall()
			if user is not None and len(user) > 0:
				if user[0][2] == 1:
					try:
						conn.simple_bind_s("MGROUP\\"+username, password)

						session['sdr_curr_user_username']	  = user[0][0].upper()
						# session['sdr_curr_user_email']	      = user[0][1]
						# session['sdr_curr_user_active']	      = user[0][2]
						session['sdr_curr_user_role']		  = user[0][3]
						# session['sdr_curr_user_dept']		  = user[0][4]
						session['sdr_loggedin']			      = True
						session['sdr_usertype']				  = 'Head Office'
						print(today, session['sdr_usertype'], session['sdr_curr_user_username'])

						next_page = request.args.get('next')
						if next_page is None:
							return redirect(url_for('index',_external=True))
						else:
							return redirect(next_page)

					except ldap.INVALID_CREDENTIALS:
						flash("Invalid Active Directory (Head Office) Domain Login")
						return redirect(url_for('index',_external=True))
				else:
					flash("SDR Portal Login is deactivated!")
					return redirect(url_for('index',_external=True))
			# store login
			else:
				sql_comm_strng2 = 'SELECT * FROM portal_store_users WITH (NOLOCK)' \
								'WHERE bcc = ?'
				store = MIS_SysDev_cursor.execute(sql_comm_strng2, (username) ).fetchall()
				# print(today, "store", store)

				if store is not None and len(store) > 0:
					domain_username = store[0][1]
					print("domain_username", domain_username)
					try:
						conn.simple_bind_s("MGROUP\\"+domain_username, password)

						session['sdr_curr_user_username'] 	  = username.upper()
						session['sdr_curr_user_company'] 	  = store[0][3]
						session['sdr_curr_user_role']		  = ''
						session['sdr_loggedin']			      = True
						session['sdr_usertype']				  = 'Store'
						# session['earliest_missing_date']	  = '2025-06-23'

						today						  		  = date.today()
						ante_date_int						  = store[0][4]
						ante_date_dt						  = (today - timedelta(days=ante_date_int))
						print("ante_date_dt", ante_date_dt, type(ante_date_dt))
						session['ante_date_int']			  = ante_date_int
						session['ante_date']				  = ante_date_dt
						session['earliest_missing_date'] 	  = generate_earliest_missing_date(ante_date_int)
						print(today, session['sdr_usertype'], session['sdr_curr_user_username'])

						next_page = request.args.get('next')
						if next_page is None:
							return redirect(url_for('index',_external=True))
						else:
							return redirect(next_page)

					except ldap.INVALID_CREDENTIALS:
						flash("Invalid Active Directory (Store) Domain Login")
						return redirect(url_for('index',_external=True))
				else:
					flash("Invalid SDR Portal Login - username does not exists !")
					return redirect(url_for('index',_external=True))


		except pyodbc.Error as e:
			flash(f"Error: {e}")
			return redirect(url_for('index',_external=True))

		except Exception as e:
			flash(f"Error: {e}")
			return redirect(url_for('index',_external=True))

		finally:
			MIS_SysDev_cursor.close()
			MIS_SysDev_connect.close()
			del MIS_SysDev_cursor
			del MIS_SysDev_connect

	return render_template('home.html')



@app.route('/logout')
@loggedin_required()
def logout():
	# print("logout", session['sdr_loggedin'])

	session.pop('sdr_loggedin', None)
	session.pop('sdr_curr_user_username', None)
	# session.pop('sdr_curr_user_active', None)
	session.pop('sdr_curr_user_role', None)
	# session.pop('sdr_curr_user_dept', None)
	session.pop('sdr_usertype', None)
	if 'earliest_missing_date' in session:
		session.pop('earliest_missing_date', None)
	if 'ante_date' in session:
		session.pop('ante_date', None)
	if 'sdr_curr_user_company' in session:
		session.pop('sdr_curr_user_company', None)

	return redirect(url_for('index',_external=True))



if __name__ == '__main__':
	app.run()
	# print("SDR Portal: 722")
	# serve(app, host='mgsvr06.mgroup.local', port=722, threads=30, connection_limit=1000)
