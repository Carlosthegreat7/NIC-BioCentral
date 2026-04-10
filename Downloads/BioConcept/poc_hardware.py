import socket
from zk import ZK
import time

#NIC BIO CENTRAL SUGGESTED APP NAME 

def test_connectivity(ip, port=4370, timeout=5):
    print(f"[{ip}] Validating TCP route...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        print(f"[{ip}] TCP Port {port} is OPEN. Network routing is valid.")
        return True
    except Exception as e:
        print(f"[{ip}] Connectivity failed: {e}")
        return False
    finally:
        s.close()

def test_enrollment(ip, test_employee_id="99999"):
    print(f"[{ip}] Initiating pyzk handshake...")
    zk = ZK(ip, port=4370, timeout=10)
    conn = None
    try:
        start_time = time.time()
        conn = zk.connect()
        handshake_time = time.time() - start_time
        print(f"[{ip}] Handshake successful in {handshake_time:.2f}s.")
        
        print(f"[{ip}] Sending start_enroll command for ID {test_employee_id}...")
        # WARNING: The device at the store should beep immediately here.
        result = conn.start_enroll(test_employee_id, temp_id=0, flag=1)
        
        if result:
            print(f"[{ip}] SUCCESS: Device accepted enrollment mode.")
        else:
            print(f"[{ip}] FAIL: Device rejected command (might be in use).")
            
    except Exception as e:
        print(f"[{ip}] Hardware communication failed: {e}")
    finally:
        if conn: conn.disconnect()

# Run the test
target_ip = "10.x.x.x" # Insertremote store IP 
if test_connectivity(target_ip):
    test_enrollment(target_ip)