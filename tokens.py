import requests
import json
import base64
import gzip
import time
import re
from urllib.parse import urlencode

def parse_proxy_string(proxy_string):
    pattern = r'(.+?):(.+?)@(.+?):(\d+)'
    match = re.match(pattern, proxy_string)
    if match:
        return {
            'username': match.group(1),
            'password': match.group(2),
            'host': match.group(3),
            'port': match.group(4)
        }
    return None

def make_request_with_proxy(url, headers, data=None, method='POST', proxy=None, is_gzip=False, is_json=True):
    session = requests.Session()
    
    proxies = None
    if proxy:
        proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
    
    try:
        if method == 'POST':
            if is_gzip:
                response = session.post(url, headers=headers, data=data, proxies=proxies, timeout=30)
            else:
                if is_json:
                    response = session.post(url, headers=headers, json=data, proxies=proxies, timeout=30)
                else:
                    response = session.post(url, headers=headers, data=data, proxies=proxies, timeout=30)
        else:
            response = session.get(url, headers=headers, proxies=proxies, timeout=30)
        
        return response.content, response.status_code
    except Exception as e:
        return str(e).encode(), 500

def decode_gzip_response(response):
    try:
        if isinstance(response, bytes):
            if response[:2] == b'\x1f\x8b':
                return gzip.decompress(response).decode('utf-8', errors='ignore')
        return response.decode('utf-8', errors='ignore') if isinstance(response, bytes) else response
    except:
        return response

def make_lyft_request(card_bin, access_token, session_id, proxy):
    url = 'https://api.lyft.com/v1/tokenization_strategies'
    time10 = str(int(time.time()))
    time13 = str(int(time.time() * 1000))
    
    headers = {
        'User-Agent': f'lyft:android:13:2025.41.3.{time10}',
        'Accept': 'application/x-protobuf,application/json',
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/json',
        'x-idl-source': 'pb.api.endpoints.v1.token_strategies.PostTokenizationStrategiesRequest',
        'authorization': f'Bearer {access_token}',
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
        'x-timestamp-source': 'ntp; age=131539',
        'content-type': 'application/json;messageType=pb.api.endpoints.v1.token_strategies.PostTokenizationStrategiesRequest; charset=utf-8',
    }
    
    data = {"purpose": 1, "card_request": {"bin": card_bin, "last_four": ""}}
    
    return make_request_with_proxy(url, headers, data, 'POST', proxy)

def extract_tokens_from_response(response, card_no, cvv):
    stripe_api_key = ''
    first_data_key = ''
    braintree_basic_token = ''
    braintree_api_base64 = ''
    chase_url = None
    
    response_str = decode_gzip_response(response)
    
    if response_str:
        chase_match = re.search(r'https://safetechpageencryption\.chasepaymentech\.com/pie/v1/[A-Za-z0-9]+/getkey\.js', response_str)
        if chase_match:
            chase_url = chase_match.group(0)
        
        stripe_match = re.search(r'pk_live_[A-Za-z0-9]+', response_str)
        if stripe_match:
            stripe_api_key = stripe_match.group(0)
        
        first_data_match = re.search(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', response_str)
        if first_data_match:
            first_data_key = first_data_match.group(0)
        
        base64_matches = re.findall(r'[A-Za-z0-9+/]{100,}={0,2}', response_str)
        for match in base64_matches:
            try:
                decoded = base64.b64decode(match)
                decoded_str = decoded.decode('utf-8', errors='ignore')
                if 'authorizationFingerprint' in decoded_str:
                    braintree_api_base64 = match
                    break
            except:
                continue
        
        if braintree_api_base64:
            try:
                decoded = base64.b64decode(braintree_api_base64)
                braintree_data = json.loads(decoded)
                if 'authorizationFingerprint' in braintree_data:
                    braintree_basic_token = braintree_data['authorizationFingerprint']
            except:
                pass
    
    return {
        'stripe_api_key': stripe_api_key,
        'first_data_key': first_data_key,
        'braintree_basic_token': braintree_basic_token,
        'braintree_api_base64': braintree_api_base64,
        'chase_url': chase_url
    }

def make_stripe_request(stripe_api_key, card_no, cvv, f_exp_month, exp_year, zipcode, proxy):
    url = 'https://api.stripe.com/v1/tokens'
    
    headers = {
        'User-Agent': 'okhttp/4.12.0',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/x-www-form-urlencoded',
        'x-idl-source': 'create_card_token_request_form_dto',
        'authorization': f'Bearer {stripe_api_key}',
        'stripe-version': '2015-10-12'
    }
    
    data = {
        'card[number]': card_no,
        'card[cvc]': cvv,
        'card[exp_month]': f_exp_month,
        'card[exp_year]': exp_year,
        'card[address_zip]': zipcode
    }
    
    response_content, status_code = make_request_with_proxy(url, headers, data, 'POST', None, is_json=False)
    
    if status_code == 200:
        try:
            response_data = json.loads(decode_gzip_response(response_content))
            return response_data.get('id')
        except:
            pass
    
    return None

def make_first_data_request(first_data_key, card_no, cvv, exp_month, f_exp_year, zipcode, proxy):
    url = 'https://api.paysecure.acculynk.net/ClientTokenizeCard'
    
    headers = {
        'User-Agent': 'okhttp/4.12.0',
        'Connection': 'Keep-Alive',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip',
        'x-idl-source': 'pb.api.endpoints.first_data.CreateClientTokenizeCardRequest',
        'Content-Type': 'application/json;messageType=pb.api.endpoints.first_data.CreateClientTokenizeCardRequest; charset=utf-8'
    }
    
    data = {
        "Version": 4,
        "SessionId": first_data_key,
        "CardNumber": card_no,
        "Expiration": exp_month + f_exp_year,
        "CVN": cvv,
        "AVS": {"Zip": zipcode}
    }
    
    response_content, status_code = make_request_with_proxy(url, headers, data, 'POST', proxy)
    
    if status_code == 200:
        try:
            response_data = json.loads(decode_gzip_response(response_content))
            if response_data.get('ErrorCode') == '00':
                return True
        except:
            pass
    
    return False

def make_braintree_request(braintree_basic_token, card_no, cvv, exp_year, f_exp_month, zipcode, proxy):
    url = 'https://payments.braintree-api.com/graphql'
    
    headers = {
        'User-Agent': 'okhttp/4.12.0',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip',
        'x-idl-source': 'pb.api.endpoints.braintree.CreateClientTokenizeCardRequest',
        'braintree-version': '2020-06-16',
        'authorization': f'Basic {braintree_basic_token}',
        'content-type': 'application/json;messageType=pb.api.endpoints.braintree.CreateClientTokenizeCardRequest; charset=utf-8',
    }
    
    query_data = {
        "query": "mutation CardTokenization($number:String,$expirationYear:String,$expirationMonth:String,$cvv:String,$postalCode:String){tokenizeCreditCard(input:{creditCard:{number:$number,expirationYear:$expirationYear,expirationMonth:$expirationMonth,cvv:$cvv,billingAddress:{postalCode:$postalCode}}}){paymentMethod{id}}}",
        "variables": {
            "number": card_no,
            "expirationYear": exp_year,
            "expirationMonth": f_exp_month,
            "cvv": cvv,
            "postalCode": zipcode
        }
    }
    
    response_content, status_code = make_request_with_proxy(url, headers, query_data, 'POST', proxy)
    
    if status_code == 200:
        try:
            response_data = json.loads(decode_gzip_response(response_content))
            if 'data' in response_data and 'tokenizeCreditCard' in response_data['data']:
                return response_data['data']['tokenizeCreditCard']['paymentMethod']['id']
        except:
            pass
    
    return None

def card_submit(access_token, session_id, stripe_token, first_data_token, braintree_token, f_exp_year, exp_month, zipcode, proxy):
    time10 = str(int(time.time()))
    time13 = str(int(time.time() * 1000))
    url = 'https://api.lyft.com/charge-accounts-multi-provider'
    
    headers = {
        'User-Agent': f'lyft:android:13:2025.41.3.{time10}',
        'Accept': 'application/x-protobuf,application/json',
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/json',
        'x-idl-source': 'pb.api.endpoints.charge_accounts.CreateChargeAccountMultipleProviderRequest',
        'authorization': f'Bearer {access_token}',
        'content-encoding': 'gzip',
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
        'x-timestamp-source': 'ntp; age=132973',
        'content-type': 'application/json;messageType=pb.api.endpoints.charge_accounts.CreateChargeAccountMultipleProviderRequest; charset=utf-8'
    }
    
    data = {
        "clientPaymentMethod": "card",
        "default": True,
        "provider_representation": [
            {
                "provider": "stripe",
                "token": stripe_token,
                "version": 1
            },
            {
                "provider": "first_data",
                "token": first_data_token
            },
            {
                "provider": "braintree",
                "token": braintree_token
            }
        ],
        "card_meta_data": {
            "expiration_month": exp_month,
            "expiration_year": f_exp_year,
            "postal_code": zipcode,
            "added_via_nfc": False
        },
        "skip_debt_collection": False,
        "skip_persisted_challenge": False
    }
    
    json_data = json.dumps(data)
    compressed_data = gzip.compress(json_data.encode('utf-8'))
    
    return make_request_with_proxy(url, headers, compressed_data, 'POST', proxy, is_gzip=True, is_json=False)

def process_tokens():
    from flask import request, jsonify
    
    submit_action = request.args.get('submit')
    
    if submit_action == "Get_Tokens":
        card_no = request.args.get('cardNo')
        exp_month = request.args.get('exp_month')
        exp_year = request.args.get('exp_year')
        cvv = request.args.get('cvv')
        zipcode = request.args.get('zipcode')
        session_id = request.args.get('SessionId')
        access_token_encoded = request.args.get('access_token')
        proxy_req = request.args.get('proxy', 'no')
        
        try:
            access_token = base64.b64decode(access_token_encoded).decode('utf-8')
        except:
            return jsonify({'error': 'Invalid access token encoding'})
        
        proxy = None
        if proxy_req == 'yes':
            try:
                with open("proxy.txt", "r") as f:
                    proxy_file = f.read().strip()
                    proxy = parse_proxy_string(proxy_file)
            except:
                proxy = None
        
        if card_no:
            card_bin = card_no[:6]
            f_exp_month = int(exp_month)
            f_exp_year = exp_year[-2:]
        
        lyft_response = make_lyft_request(card_bin, access_token, session_id, proxy)
        
        if lyft_response and lyft_response[1] == 200:
            tokens = extract_tokens_from_response(lyft_response[0], card_no, cvv)
            final_results = {
                'stripe_id': None,
                'first_data_key': tokens['first_data_key'],
                'braintree_id': None,
                'chase_url': tokens['chase_url']
            }
            
            if tokens['stripe_api_key']:
                stripe_id = make_stripe_request(tokens['stripe_api_key'], card_no, cvv, f_exp_month, exp_year, zipcode, proxy)
                final_results['stripe_id'] = stripe_id
            
            if tokens['first_data_key']:
                first_data_success = make_first_data_request(tokens['first_data_key'], card_no, cvv, exp_month, f_exp_year, zipcode, proxy)
                if not first_data_success:
                    final_results['first_data_key'] = None
            
            if tokens['braintree_basic_token']:
                braintree_id = make_braintree_request(tokens['braintree_basic_token'], card_no, cvv, exp_year, exp_month, zipcode, proxy)
                final_results['braintree_id'] = braintree_id
            
            return jsonify(final_results)
        else:
            error_msg = "Failed to get response from Lyft API"
            if lyft_response:
                error_msg += f" - HTTP Code: {lyft_response[1]}"
            return jsonify({'error': error_msg, 'rawData': lyft_response[0] if lyft_response else None})
    
    elif submit_action == "Submit_card":
        card_no = request.args.get('cardNo')
        exp_month = request.args.get('exp_month')
        exp_year = request.args.get('exp_year')
        cvv = request.args.get('cvv')
        zipcode = request.args.get('zipcode')
        session_id = request.args.get('SessionId')
        access_token_encoded = request.args.get('access_token')
        stripe_token = request.args.get('stripe_token')
        first_data_token = request.args.get('first_data_token')
        braintree_token = request.args.get('braintree_token')
        proxy_req = request.args.get('proxy', 'no')
        
        try:
            access_token = base64.b64decode(access_token_encoded).decode('utf-8')
        except:
            return jsonify({'error': 'Invalid access token encoding'})
        
        proxy = None
        if proxy_req == 'yes':
            try:
                with open("proxy.txt", "r") as f:
                    proxy_file = f.read().strip()
                    proxy = parse_proxy_string(proxy_file)
            except:
                proxy = None
        
        f_exp_year = exp_year[-2:]
        
        card_response = card_submit(access_token, session_id, stripe_token, first_data_token, braintree_token, f_exp_year, exp_month, zipcode, proxy)
        
        if card_response:
            final_results = {
                'success': card_response[1] == 200,
                'response_data': card_response[0].decode('utf-8', errors='ignore') if isinstance(card_response[0], bytes) else card_response[0],
                'httpCode': card_response[1]
            }
        else:
            final_results = {
                'success': False,
                'response_data': None,
                'httpCode': 500
            }
        return jsonify(final_results)
    
    return jsonify({'error': 'Invalid action'})