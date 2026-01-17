# Payments API routes - WayForPay, Monobank integration
# Extracted from app.py for better code organization

import os
import json
import hmac
import hashlib
import uuid
import logging
import traceback
from datetime import datetime

import requests
import pytz
from flask import Blueprint, jsonify, request

from .config import (
    WAYFORPAY_MERCHANT_ACCOUNT,
    WAYFORPAY_MERCHANT_SECRET,
    WAYFORPAY_DOMAIN,
    WAYFORPAY_ENABLED,
    MONOBANK_TOKEN,
    MONOBANK_ENABLED,
    COMMERCIAL_SUBSCRIPTIONS_FILE,
    get_kyiv_now,
)

log = logging.getLogger(__name__)

# Create blueprint
payments_bp = Blueprint('payments', __name__)

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================
def generate_wayforpay_signature(params, secret_key):
    """Generate HMAC_MD5 signature for WayForPay."""
    sign_string = ';'.join(str(p) for p in params)
    return hmac.new(
        secret_key.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.md5
    ).hexdigest()


def load_subscriptions():
    """Load subscriptions from file."""
    subscriptions = []
    if os.path.exists(COMMERCIAL_SUBSCRIPTIONS_FILE):
        try:
            with open(COMMERCIAL_SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
                subscriptions = json.load(f)
        except Exception:
            pass
    return subscriptions


def save_subscriptions(subscriptions):
    """Save subscriptions to file."""
    with open(COMMERCIAL_SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(subscriptions, f, ensure_ascii=False, indent=2)


# =============================================================================
# WAYFORPAY ROUTES
# =============================================================================
@payments_bp.route('/api/wayforpay/create-invoice', methods=['POST'])
def wayforpay_create_invoice():
    """Create WayForPay invoice with unique order ID."""
    try:
        data = request.get_json() or {}
        
        # Generate unique order ID
        import time
        order_id = f"NEPTUN_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Get client info
        client_name = data.get('name', 'Клієнт NEPTUN')
        client_telegram = data.get('telegram', '')
        client_type = data.get('type', 'Комерційна підписка')
        amount = int(data.get('amount', 1000))
        
        # Save subscription request
        subscription = {
            'id': order_id,
            'name': client_name,
            'telegram': client_telegram,
            'type': client_type,
            'amount': amount,
            'currency': 'UAH',
            'status': 'pending',
            'timestamp': get_kyiv_now().isoformat(),
            'ip': request.remote_addr
        }
        
        subscriptions = load_subscriptions()
        subscriptions.append(subscription)
        save_subscriptions(subscriptions)
        
        log.info(f"🔔 NEW WAYFORPAY ORDER: {order_id}")
        log.info(f"   Name: {client_name}, Telegram: {client_telegram}")
        log.info(f"   Amount: {amount} UAH")
        
        if WAYFORPAY_ENABLED:
            import time as _time
            order_date = int(_time.time())
            
            product_name = 'Комерційна підписка NEPTUN (місяць)'
            product_count = 1
            product_price = amount
            
            sign_string = f"{WAYFORPAY_MERCHANT_ACCOUNT};{WAYFORPAY_DOMAIN};{order_id};{order_date};{amount};UAH;{product_name};{product_count};{product_price}"
            
            signature = hmac.new(
                WAYFORPAY_MERCHANT_SECRET.encode('utf-8'),
                sign_string.encode('utf-8'),
                hashlib.md5
            ).hexdigest()
            
            invoice_data = {
                'transactionType': 'CREATE_INVOICE',
                'merchantAccount': WAYFORPAY_MERCHANT_ACCOUNT,
                'merchantDomainName': WAYFORPAY_DOMAIN,
                'merchantSignature': signature,
                'apiVersion': 1,
                'orderReference': order_id,
                'orderDate': order_date,
                'amount': amount,
                'currency': 'UAH',
                'productName': [product_name],
                'productCount': [product_count],
                'productPrice': [product_price],
                'returnUrl': 'https://neptun.in.ua/?payment=success',
                'serviceUrl': 'https://neptun.in.ua/api/wayforpay/callback',
                'language': 'UA'
            }
            
            try:
                response = requests.post(
                    'https://api.wayforpay.com/api',
                    json=invoice_data,
                    timeout=10
                )
                
                result = response.json()
                log.info(f"   WayForPay response: {result}")
                
                if result.get('reasonCode') == 1100:
                    invoice_url = result.get('invoiceUrl')
                    log.info(f"✅ WayForPay invoice created: {invoice_url}")
                    
                    return jsonify({
                        'success': True,
                        'order_id': order_id,
                        'payment_url': invoice_url,
                        'message': 'Рахунок створено'
                    })
                else:
                    error_msg = result.get('reason', 'Unknown error')
                    log.error(f"❌ WayForPay error: {error_msg}")
                    return jsonify({
                        'success': False,
                        'order_id': order_id,
                        'error': f'WayForPay помилка: {error_msg}',
                        'error_detail': result
                    }), 400
                    
            except Exception as e:
                log.error(f"❌ WayForPay API error: {e}")
                traceback.print_exc()
                return jsonify({
                    'success': False,
                    'order_id': order_id,
                    'error': f'WayForPay API помилка: {str(e)}'
                }), 500
        
        return jsonify({
            'success': False,
            'error': 'WayForPay не налаштований на сервері'
        }), 500
        
    except Exception as e:
        log.error(f"❌ WayForPay create invoice error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@payments_bp.route('/api/wayforpay/callback', methods=['POST'])
def wayforpay_callback():
    """Handle WayForPay webhook after payment."""
    try:
        data = request.get_json() or {}
        
        order_id = data.get('orderReference', '')
        status = data.get('transactionStatus', '')
        
        log.info(f"💳 WayForPay callback: {order_id} - {status}")
        
        # Update subscription status
        subscriptions = load_subscriptions()
        for sub in subscriptions:
            if sub.get('id') == order_id:
                sub['status'] = 'paid' if status == 'Approved' else status
                sub['payment_date'] = get_kyiv_now().isoformat()
                break
        save_subscriptions(subscriptions)
        
        log.info(f"✅ Subscription {order_id} updated to: {status}")
        
        # Return response signature
        response_time = int(datetime.now().timestamp())
        sign_params = [order_id, status, response_time]
        
        signature = ''
        if WAYFORPAY_ENABLED:
            signature = generate_wayforpay_signature(sign_params, WAYFORPAY_MERCHANT_SECRET)
        
        return jsonify({
            'orderReference': order_id,
            'status': 'accept',
            'time': response_time,
            'signature': signature
        })
        
    except Exception as e:
        log.error(f"❌ WayForPay callback error: {e}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# COMMERCIAL SUBSCRIPTION (with Monobank option)
# =============================================================================
@payments_bp.route('/api/commercial_subscription', methods=['POST'])
def commercial_subscription():
    """Handle commercial subscription requests with Monobank payment."""
    try:
        data = request.get_json()
        
        required_fields = ['name', 'telegram', 'type']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        subscription = {
            'id': str(uuid.uuid4()),
            'name': data.get('name'),
            'telegram': data.get('telegram'),
            'type': data.get('type'),
            'comment': data.get('comment', ''),
            'amount': data.get('amount', 1500),
            'currency': 'UAH',
            'status': 'pending',
            'timestamp': get_kyiv_now().isoformat(),
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', '')
        }
        
        subscriptions = load_subscriptions()
        subscriptions.append(subscription)
        save_subscriptions(subscriptions)
        
        log.info(f"🔔 NEW COMMERCIAL SUBSCRIPTION:")
        log.info(f"   ID: {subscription['id']}")
        log.info(f"   Name: {subscription['name']}")
        log.info(f"   Telegram: {subscription['telegram']}")
        log.info(f"   Type: {subscription['type']}")
        log.info(f"   Amount: {subscription['amount']} UAH")
        
        payment_url = None
        invoice_id = None
        
        if MONOBANK_ENABLED:
            try:
                order_reference = subscription['id']
                amount = subscription['amount']
                
                invoice_payload = {
                    'amount': amount * 100,  # Monobank uses cents
                    'ccy': 980,  # UAH
                    'merchantPaymInfo': {
                        'reference': order_reference,
                        'destination': f"Підписка NEPTUN: {subscription['type']}",
                        'basketOrder': [
                            {
                                'name': f"Комерційна підписка {subscription['type']}",
                                'qty': 1,
                                'sum': amount * 100,
                                'code': 'subscription'
                            }
                        ]
                    },
                    'redirectUrl': 'https://neptun.in.ua/?payment=success',
                    'webHookUrl': 'https://neptun.in.ua/api/monobank_callback'
                }
                
                response = requests.post(
                    'https://api.monobank.ua/api/merchant/invoice/create',
                    headers={
                        'X-Token': MONOBANK_TOKEN,
                        'Content-Type': 'application/json'
                    },
                    json=invoice_payload,
                    timeout=10
                )
                
                if response.ok:
                    result = response.json()
                    payment_url = result.get('pageUrl')
                    invoice_id = result.get('invoiceId')
                    log.info(f"✅ Monobank invoice created: {invoice_id}")
                else:
                    log.error(f"Monobank error: {response.text}")
                    
            except Exception as e:
                log.error(f"Monobank API error: {e}")
        
        return jsonify({
            'success': True,
            'subscription_id': subscription['id'],
            'payment_url': payment_url,
            'invoice_id': invoice_id,
            'message': 'Заявку прийнято!' if not payment_url else 'Перейдіть до оплати'
        })
        
    except Exception as e:
        log.error(f"Commercial subscription error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@payments_bp.route('/api/monobank_callback', methods=['POST'])
def monobank_callback():
    """Handle Monobank payment webhook."""
    try:
        data = request.get_json() or {}
        
        invoice_id = data.get('invoiceId', '')
        status = data.get('status', '')
        reference = data.get('reference', '')
        
        log.info(f"💳 Monobank callback: {invoice_id} - {status} (ref: {reference})")
        
        if status == 'success':
            subscriptions = load_subscriptions()
            for sub in subscriptions:
                if sub.get('id') == reference:
                    sub['status'] = 'paid'
                    sub['payment_date'] = get_kyiv_now().isoformat()
                    sub['monobank_invoice_id'] = invoice_id
                    break
            save_subscriptions(subscriptions)
            log.info(f"✅ Subscription {reference} marked as paid via Monobank")
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        log.error(f"Monobank callback error: {e}")
        return jsonify({'error': str(e)}), 500
