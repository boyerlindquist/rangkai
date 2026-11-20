"""
Sumopod Managed Payment API client & webhook verifier.
Supports QRIS payment creation, status verification, X-Webhook-Token,
and Svix HMAC-SHA256 webhook signature verification.
"""
import base64
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class SumopodError(Exception):
    """Raised when Sumopod API returns an error or network call fails."""

    def __init__(self, message, status_code=None, raw_body=None):
        super().__init__(message)
        self.status_code = status_code
        self.raw_body = raw_body


def is_configured():
    """Return True when SUMOPOD_API_KEY is configured in environment."""
    return bool(getattr(settings, 'SUMOPOD_API_KEY', '').strip())


def parse_iso_datetime(value):
    """Parse ISO-8601 timestamp string (e.g. '2026-06-18T12:00:00Z') to aware datetime."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if timezone.is_aware(value) else timezone.make_aware(value, dt_timezone.utc)
    try:
        text = str(value).strip()
        if text.endswith('Z'):
            text = text[:-1] + '+00:00'
        parsed = datetime.fromisoformat(text)
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, dt_timezone.utc)
        return parsed
    except (ValueError, TypeError):
        return None


def _api_request(method, path, payload=None, timeout=15):
    """Send an authenticated JSON request to Sumopod Managed Payment API."""
    api_key = getattr(settings, 'SUMOPOD_API_KEY', '').strip()
    if not api_key:
        raise SumopodError('SUMOPOD_API_KEY belum dikonfigurasi.')

    base_url = getattr(
        settings,
        'SUMOPOD_BASE_URL',
        'https://api-pay-sandbox.sumopod.com/api/v1',
    ).rstrip('/')
    url = f'{base_url}/{path.lstrip("/")}'

    body_bytes = None
    headers = {
        'X-Api-Key': api_key,
        'Accept': 'application/json',
        'User-Agent': 'RangkaiClick/1.0',
    }
    if payload is not None:
        body_bytes = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'

    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode('utf-8')
            data = json.loads(raw) if raw else {}
            if isinstance(data, dict) and isinstance(data.get('data'), dict):
                return data['data']
            return data
    except urllib.error.HTTPError as exc:
        raw_err = exc.read().decode('utf-8', errors='replace')
        err_msg = f'Sumopod API error (HTTP {exc.code})'
        try:
            err_json = json.loads(raw_err)
            if isinstance(err_json, dict):
                base_msg = err_json.get('message') or err_json.get('error') or err_msg
                details = err_json.get('details')
                err_msg = f'{base_msg}: {details}' if details else base_msg
        except json.JSONDecodeError:
            pass
        logger.warning('Sumopod API HTTPError %s on %s: %s', exc.code, path, raw_err[:400])
        raise SumopodError(err_msg, status_code=exc.code, raw_body=raw_err) from exc
    except urllib.error.URLError as exc:
        logger.warning('Sumopod API URLError on %s: %s', path, exc)
        raise SumopodError(f'Gagal terhubung ke Sumopod: {exc.reason}') from exc
    except (json.JSONDecodeError, TimeoutError) as exc:
        logger.warning('Sumopod API response error on %s: %s', path, exc)
        raise SumopodError('Respons dari Sumopod tidak valid atau timeout.') from exc


def create_payment(
    order_id,
    amount,
    success_return_url,
    cancel_return_url,
    payment_method_type_code='QRIS',
    expires_in_hours=None,
):
    """
    Create a payment transaction via POST /api/v1/payments.
    Returns normalized payment dict with payment_id, payment_link_url, status, expires_at, etc.
    """
    if expires_in_hours is None:
        expires_in_hours = getattr(settings, 'SUMOPOD_EXPIRES_IN_HOURS', 24)

    payload = {
        'order_id': str(order_id),
        'amount': int(amount),
        'currency': 'IDR',
        'expires_in_hours': int(expires_in_hours),
        'payment_method_type_code': payment_method_type_code,
    }
    # Sumopod enforces valid public HTTPS URLs for redirecturl validation;
    # omit them on local http:// dev so payment creation succeeds cleanly.
    if success_return_url and str(success_return_url).startswith('https://'):
        payload['success_return_url'] = str(success_return_url)
    if cancel_return_url and str(cancel_return_url).startswith('https://'):
        payload['cancel_return_url'] = str(cancel_return_url)
    data = _api_request('POST', '/payments', payload=payload)
    return {
        'payment_id': data.get('payment_id') or data.get('id') or '',
        'order_id': data.get('order_id') or order_id,
        'amount': data.get('amount', int(amount)),
        'fee': data.get('fee', 0) or 0,
        'net_amount': data.get('net_amount', int(amount)) or 0,
        'payment_link_url': data.get('payment_link_url') or '',
        'payment_code': data.get('payment_code') or '',
        'status': (data.get('status') or 'pending').lower(),
        'expires_at': parse_iso_datetime(data.get('expires_at')),
        'raw': data,
    }


def get_payment_status(payment_id):
    """
    Fetch current payment status via GET /api/v1/payments/{payment_id}.
    """
    if not payment_id:
        raise SumopodError('payment_id kosong.')
    data = _api_request('GET', f'/payments/{payment_id}')
    return {
        'payment_id': data.get('payment_id') or data.get('id') or payment_id,
        'order_id': data.get('order_id') or '',
        'amount': data.get('amount'),
        'fee': data.get('fee', 0) or 0,
        'net_amount': data.get('net_amount', 0) or 0,
        'payment_link_url': data.get('payment_link_url') or '',
        'status': (data.get('status') or 'pending').lower(),
        'paid_at': parse_iso_datetime(data.get('paid_at') or data.get('completed_at')),
        'expires_at': parse_iso_datetime(data.get('expires_at')),
        'raw': data,
    }


def verify_webhook_token(received_token, expected_token=None):
    """Verify static X-Webhook-Token header (whtok_...)."""
    expected = (expected_token if expected_token is not None else getattr(settings, 'SUMOPOD_WEBHOOK_TOKEN', '')).strip()
    received = (received_token or '').strip()
    if not expected or not received:
        return False
    return hmac.compare_digest(expected, received)


def verify_webhook_signature(svix_id, svix_timestamp, svix_signature, raw_body, secret=None):
    """
    Verify Svix-style HMAC-SHA256 webhook signature (whsec_...).
    Matches Sumopod's official verification algorithm.
    """
    secret_val = (secret if secret is not None else getattr(settings, 'SUMOPOD_WEBHOOK_SECRET', '')).strip()
    if not secret_val or not svix_id or not svix_timestamp or not svix_signature:
        return False

    try:
        clean_secret = secret_val[6:] if secret_val.startswith('whsec_') else secret_val
        secret_bytes = base64.b64decode(clean_secret)
    except Exception:
        return False

    body_str = raw_body.decode('utf-8') if isinstance(raw_body, (bytes, bytearray)) else str(raw_body)
    signed_content = f'{svix_id}.{svix_timestamp}.{body_str}'.encode('utf-8')
    expected_sig = base64.b64encode(
        hmac.new(secret_bytes, signed_content, hashlib.sha256).digest()
    ).decode('utf-8')

    for entry in str(svix_signature).split(' '):
        parts = entry.split(',', 1)
        if len(parts) == 2 and hmac.compare_digest(parts[1], expected_sig):
            return True
    return False


def verify_webhook_request(headers, raw_body):
    """
    Verify incoming Sumopod webhook using either X-Webhook-Token or Svix HMAC signature.
    Fails closed if neither secret/token is configured.
    """
    token = headers.get('X-Webhook-Token') or headers.get('x-webhook-token') or ''
    if verify_webhook_token(token):
        return True

    svix_id = headers.get('svix-id') or headers.get('Svix-Id') or ''
    svix_ts = headers.get('svix-timestamp') or headers.get('Svix-Timestamp') or ''
    svix_sig = headers.get('svix-signature') or headers.get('Svix-Signature') or ''
    if verify_webhook_signature(svix_id, svix_ts, svix_sig, raw_body):
        return True

    return False


def forward_webhook(target_url, incoming_headers, raw_body, timeout=8):
    """
    Forward a raw Sumopod webhook (exact bytes + auth/Svix headers) to another app
    (e.g. TickerWatch) when sharing a single Sumopod Managed Payment project.
    Returns (status_code, response_text).
    """
    forward_headers = {
        'Content-Type': incoming_headers.get('Content-Type') or 'application/json',
        'User-Agent': 'RangkaiClick-WebhookForwarder/1.0',
    }
    for key in ('X-Webhook-Token', 'svix-id', 'svix-timestamp', 'svix-signature'):
        val = incoming_headers.get(key) or incoming_headers.get(key.lower())
        if val:
            forward_headers[key] = val

    body_bytes = raw_body if isinstance(raw_body, (bytes, bytearray)) else str(raw_body).encode('utf-8')
    req = urllib.request.Request(target_url, data=body_bytes, headers=forward_headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        logger.warning('Forwarded webhook to %s returned HTTP %s', target_url, exc.code)
        return exc.code, body
    except Exception as exc:
        logger.warning('Failed forwarding webhook to %s: %s', target_url, exc)
        return 502, str(exc)
