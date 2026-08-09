import pytz
import stripe
from datetime import datetime, timezone
from flask import Blueprint, current_app, jsonify, request, url_for

from ..config import WEBHOOK_PREM
from ..db import get_guild
from ..consts import premium_types
from ..utils import bearer_client

from modules import bot as v
from modules.models import Guild

stripe_bp = Blueprint('stripe', __name__)

# ── Checkout session ──────────────────────────────────────────────────────────
@stripe_bp.route('/<int:guild_id>/stripe/pay/<type>')
def stripe_pay(guild_id, type):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)

    existing = stripe.Customer.list(email=current_user.email).data
    if existing:
        customer_id = existing[0].id
    else:
        customer_id = stripe.Customer.create(
            email=current_user.email,
            name=current_user.username
        ).id

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{'price': premium_types[type]['price_id'], 'quantity': 1}],
        mode=premium_types[type]['mode'],
        customer=customer_id,
        success_url=url_for('dashboard.premium', _external=True, guild_id=guild.id) + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=url_for('dashboard.premium', _external=True, guild_id=guild.id),
        metadata={"guild_id": guild.id, "user_id": current_user.id}
    )
    return {'checkout_session_id': session['id'], 'checkout_public_key': current_app.config['STRIPE_PUBLIC_KEY']}


# ── Billing portal ────────────────────────────────────────────────────────────
@stripe_bp.route('/stripe/portal/<customer_id>', methods=['POST'])
def stripe_portal(customer_id):
    # Use Bunnet to find guild with this customer
    guild_doc = Guild.find_one({"premium.customer": customer_id}).run()
    if not guild_doc:
        return {'error': 'customer id not found'}, 400

    portal = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=url_for('dashboard.premium', _external=True, guild_id=int(guild_doc.id)),
    )
    return {'url': portal["url"], 'checkout_public_key': current_app.config['STRIPE_PUBLIC_KEY']}


# ── Webhook ───────────────────────────────────────────────────────────────────
@stripe_bp.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    if request.content_length > 1024 * 1024:
        return "REQUEST TOO BIG", 400

    payload = request.get_data()
    sig_header = request.environ.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = current_app.config["STRIPE_WEBHOOK_KEY"]

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return {}, 400
    except stripe.error.SignatureVerificationError:
        return {}, 400

    handlers = {
        'checkout.session.completed':       _handle_checkout_completed,
        'customer.subscription.updated':    _handle_subscription_updated,
        'customer.subscription.deleted':    _handle_subscription_deleted,
        'invoice.paid':                     _handle_invoice_paid,
        'invoice.payment_failed':           _handle_invoice_payment_failed,
    }

    handler = handlers.get(event['type'])
    if handler:
        return handler(event['data']['object'])

    return jsonify({"status": "ignored"}), 200


def _tz_from_guild(guild_id):
    config = Guild.get(str(guild_id)).run()
    return pytz.timezone(config.settings.get('timezone', 'UTC'))


def _handle_checkout_completed(session):
    if not session:
        return {}, 400

    line_items = stripe.checkout.Session.list_line_items(session['id'], limit=1)
    guild_id = session['metadata']['guild_id']
    user_id = session['metadata']['user_id']

    # Use Bunnet to get and update the guild
    doc = Guild.get(str(guild_id)).run()
    if not doc:
        return {}, 400

    tzu = _tz_from_guild(guild_id)
    created_at = datetime.fromtimestamp(session["created"], tz=timezone.utc).astimezone(tzu)

    if session["mode"] == "subscription":
        doc.premium = {
            "id": session['subscription'],
            "status": True,
            "active": session['status'] == 'complete',
            "plan": line_items['data'][0]['description'].lower(),
            "customer": session['customer'],
            "user_id": user_id,
            "subscribed_at": created_at,
        }
    elif session["mode"] == "payment":
        doc.premium = {
            "id": session['payment_intent'],
            "status": True,
            "active": session['status'] == 'complete',
            "plan": line_items['data'][0]['description'].lower(),
            "customer": session['customer'],
            "user_id": user_id,
            "subscribed_at": created_at,
        }
    else:
        return jsonify({"status": "ignored"}), 200

    doc.save()
    return {}


def _handle_subscription_updated(subscription):
    if not subscription:
        return jsonify({"error": "Invalid subscription data"}), 400

    doc = Guild.find_one({"premium.id": subscription['id']}).run()
    if not doc:
        return jsonify({"error": "Subscription data not found"}), 400

    ptimezone = pytz.timezone(doc.settings.get('timezone', 'UTC'))

    if subscription.get('cancel_at') or subscription.get('canceled_at'):
        doc.premium['status'] = False
        doc.premium['active'] = False
        doc.save()
        return jsonify({"status": "success", "msg": "User canceled subscription"}), 200

    if not doc.premium.get('status') and not subscription.get('cancel_at'):
        doc.premium['status'] = True
        doc.premium['active'] = True
        updated_at = datetime.fromtimestamp(
            subscription["current_period_end"], tz=timezone.utc
        ).astimezone(ptimezone)
        doc.premium['subscribed_at'] = updated_at
        doc.save()
        return jsonify({"status": "success", "msg": "User subscribed to premium"}), 200

    return jsonify({"status": "success"}), 200


def _handle_subscription_deleted(subscription):
    doc = Guild.find_one({"premium.id": subscription['id']}).run()
    if not doc:
        return jsonify({"error": "Subscription not found"}), 400

    doc.premium['active'] = False
    doc.premium['status'] = False
    doc.save()
    return jsonify({"status": "success", "msg": "Subscription canceled"}), 200


def _handle_invoice_paid(invoice):
    subscription_id = invoice['subscription']
    subscription = stripe.Subscription.retrieve(subscription_id)

    doc = Guild.find_one({"premium.id": subscription_id}).run()
    if not doc:
        return jsonify({"error": "Subscription data not found"}), 400

    ptimezone = pytz.timezone(doc.settings.get('timezone', 'UTC'))

    doc.premium = {
        "id": subscription_id,
        "status": True,
        "active": True,
        "plan": subscription['items']['data'][0]['price']['nickname'].lower(),
        "customer": subscription['customer'],
        "user_id": doc.premium.get('user_id'),
        "subscribed_at": datetime.now(),
    }
    doc.save()

    renewed_at = datetime.fromtimestamp(
        subscription["current_period_end"], tz=timezone.utc
    ).astimezone(ptimezone)
    doc.premium['subscribed_at'] = renewed_at
    doc.save()

    return jsonify({"status": "success", "msg": "Invoice paid, subscription updated"}), 200


def _handle_invoice_payment_failed(invoice):
    subscription_id = invoice['subscription']
    doc = Guild.find_one({"premium.id": subscription_id}).run()
    if not doc:
        return jsonify({"error": "Subscription data not found"}), 400

    doc.premium['active'] = False
    doc.premium['status'] = False
    doc.save()
    return jsonify({"status": "success", "msg": "Invoice payment failed"}), 200