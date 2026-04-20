from flask import Blueprint, render_template, session, redirect, url_for
from portal import loggedin_required 

store_crud_bp = Blueprint('store_crud', __name__)

@store_crud_bp.route('/device-manager')
@loggedin_required()
def device_manager():
    return render_template('connect_device.html')