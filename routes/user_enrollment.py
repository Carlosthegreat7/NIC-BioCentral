import pyodbc
from flask import Blueprint, request, jsonify, render_template
from zk import ZK, const

enroll_bp = Blueprint('enroll_bp', __name__)

@enroll_bp.route('/new_fingerprint', methods=['GET'])
def new_fingerprint_page():
    return render_template('new_fingerprint.html')


# --- Enterprise DB Credentials ---
DB_SERVER = '192.168.100.115'
DB_NAME = 'HRISNICV2'
DB_UID = 'BioCentral'
DB_PWD = 'B1oC3ntr@l2026'

def fetch_employee_name(access_no):
    """Fetches the official employee name from the vBiometricsManagement view."""
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_UID};"
        f"PWD={DB_PWD};"
        f"TrustServerCertificate=yes;"
    )
    
    # Parameterized query to prevent SQL injection
    query = "SELECT [Name] FROM [dbo].[vBiometricsManagement] WHERE [AccessNo] = ?"
    
    try:
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (access_no,))
                row = cursor.fetchone()
                if row:
                    return row[0] # Returns the matched [Name]
    except pyodbc.Error as e:
        print(f"Database lookup failed: {e}")
        
    return None


# --- POST Route: Hardware API Endpoint ---
@enroll_bp.route('/api/enroll_fingerprint', methods=['POST'])
def enroll_fingerprint():
    data = request.json
    ip = data.get('ip')
    port = int(data.get('port', 4370))
    user_id = str(data.get('user_id')) # AccessNo from the frontend
    
    if not ip or not user_id:
        return jsonify({"status": "error", "message": "Store IP and Access Number are required."}), 400

    # 1. Authoritative Database Lookup
    employee_name = fetch_employee_name(user_id)
    if not employee_name:
         return jsonify({
             "status": "error", 
             "message": f"Access Number {user_id} not found in HRIS Database. Cannot enroll."
         }), 404

    # 2. Hardware Communication
    zk = ZK(ip, port=port, timeout=5, password=0, force_udp=False, ommit_ping=False)
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device() 
        
        # Ensure ID format matches your internal indexing requirement
        uid = int(user_id) 

        # Push official DB Name to the physical device
        conn.set_user(
            uid=uid, 
            name=employee_name, 
            privilege=const.USER_DEFAULT, 
            password='', 
            group_id='', 
            user_id=user_id
        )
        
        # Trigger Remote Fingerprint Enrollment (temp_id=1 for primary finger)
        conn.enroll_user(uid=uid, temp_id=1, user_id=user_id)
        
        return jsonify({
            "status": "success", 
            "message": f"Verified {employee_name}. The scanner at {ip} is now ready for their fingerprint."
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        
    finally:
        if conn:
            conn.enable_device() 
            conn.disconnect()