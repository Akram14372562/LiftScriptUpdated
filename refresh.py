import json
import time
import requests
from flask import request, jsonify
from datetime import datetime

def json_write(filename, data, number):
    try:
        with open(filename, "r") as f:
            all_data = json.load(f)
    except:
        all_data = {}
    
    all_data[number] = data
    
    with open(filename, "w") as f:
        json.dump(all_data, f, indent=2)

def get_all_details_by_count(data, count=False, number=False):
    if not number:
        keys = list(data.keys())
        if count < len(keys):
            key = keys[count]
            return data[key]
    if number:
        return data.get(number)
    return None

def refresh_token():
    number = request.args.get("number")
    ol = request.args.get('ol', 0, type=int)
    
    if not number:
        return jsonify({
            'status': 'error',
            'http_code': 400,
            'message': 'Number parameter required',
            'response': 'Please provide a number parameter'
        }), 400
    
    try:
        with open("userdata-1.json", "r") as f:
            data = json.load(f)
    except:
        return jsonify({
            'status': 'error',
            'http_code': 404,
            'message': 'File has no data or account not found',
            'response': 'File has no data'
        }), 404
    
    if data:
        count1 = len(data) - 1
        details = get_all_details_by_count(data, ol, number)
    else:
        return jsonify({
            'status': 'error',
            'http_code': 404,
            'message': 'File has no data or account not found',
            'response': 'File has no data'
        }), 404
    
    if details:
        number = details.get('number')
        access_token = details.get('access_token')
        refresh_token_val = details.get('refresh_token')
        session_id = details.get('x-client-session-id')
        call_event_id = details.get('call_event_id')
        ip = details.get('ip')
        dt = details.get('Date & time') or details.get('Created Date & time')
    else:
        return jsonify({
            'status': 'error',
            'http_code': 404,
            'message': 'File has no data or account not found',
            'response': 'File has no data'
        }), 404
    
    if not refresh_token_val:
        return jsonify({
            'status': 'error',
            'http_code': 400,
            'message': 'Refresh token missing',
            'response': 'Account over or Not Found'
        }), 400
    
    if refresh_token_val and session_id:
        time10 = str(int(time.time()))
        time13 = str(int(time.time() * 1000))

        url = 'https://api.lyft.com/oauth2/access_token'

        headers = {
            'User-Agent': f'lyft:android:13:2025.43.3.{time10}',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'Content-Type': 'application/x-www-form-urlencoded',
            'x-idl-source': 'create_access_token_request_form_data_dto',
            'x-path-template': '/oauth2/access_token',
            'authorization': 'Basic ZVNhdDctaXU5ZG9NOlp0dkxEejBuMS1rSlZ3a0l2eEM0aVNKMHlNdkp5ZFBx',
            'x-session': 'eyJhIjoiNDczZGQzNGY4MjA5NDMyZSIsImYiOiI5N2NiMmU1ZC05NmI0LTRlYTEtOTVjNC0wNGNlOGM4MzAyNjkiLCJoIjp0cnVlLCJrIjoiMzg2NjcwMzMtYzA2Mi00ZDAyLWIyNTYtOThmMDNhMmY2NThkIn0=',
            'x-client-session-id': session_id,
            'accept-language': 'en_IN',
            'user-device': 'Xiaomi Redmi Note 5 Pro',
            'x-locale-language': 'en',
            'x-locale-region': 'IN',
            'x-device-density': '440',
            'x-design-id': 'X',
            'x-location': '0.0,0.0',
            'x-timestamp-ms': time13,
            'x-timestamp-source': 'ntp; age=92716311',
            'x-call-event-span-id': call_event_id or ''
        }

        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token_val
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                data=data,
                timeout=30
            )
            
            http_code = response.status_code
            output = response.text
            
            json_data = response.json()
            access_token1 = json_data.get("access_token")
            refresh_token1 = json_data.get("refresh_token")
            user_id1 = json_data.get("user_id")

            if http_code == 200 and access_token1 and refresh_token1:
                dt1 = datetime.now().strftime("%a %d %b %Y %I:%M:%S %p")
                printdata = {
                    "number": number,
                    "access_token": access_token1,
                    "refresh_token": refresh_token1,
                    "x-client-session-id": session_id,
                    "call_event_id": call_event_id,
                    "user_id": user_id1,
                    "output": output,
                    "ip": ip,
                    "refreshed Date & time": dt1,
                    "Created Date & time": dt
                }
                
                json_write("userdata-1.json", printdata, number)
                
                return jsonify({
                    'status': 'success',
                    'http_code': 200,
                    'message': 'Token refresh successful',
                    'response': output,
                    'data': {
                        'access_token': access_token1,
                        'refresh_token': refresh_token1,
                        'user_id': user_id1
                    }
                })
                
            else:
                error_message = "Token refresh failed"
                
                return jsonify({
                    'status': 'error',
                    'http_code': http_code or 400,
                    'message': error_message,
                    'response': output
                }), http_code or 400
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'http_code': 500,
                'message': f'Request failed: {str(e)}',
                'response': str(e)
            }), 500
            
    else:
        return jsonify({
            'status': 'error',
            'http_code': 400,
            'message': 'Missing required tokens or session data',
            'response': 'Refresh token, Session ID, or Call Event ID missing'
        }), 400