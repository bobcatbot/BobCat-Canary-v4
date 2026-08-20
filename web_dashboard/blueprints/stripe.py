import asyncio
import logging
import pytz
import stripe
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from quart import Blueprint, current_app, jsonify, request, url_for

from ..consts import premium_types
from ..utils import bearer_client, check_guild_permission, login_required

from modules import bot as v
from modules.models import Guild, StripeEvent

log = logging.getLogger(__name__)

stripe_bp = Blueprint('stripe', __name__)

# Billing is money-moving, so it is restricted to the guild owner and real
# Discord administrators — custom admin/bot-master roles are not enough.
BILLING_PERMISSION_LEVELS = ("Owner", "Administrator")


def _authorize_billing(guild_id):
    """
    Resolve the guild for a billing request and authorize the session user.

    Returns (guild, doc, None) on success or (None, None, (body, status)) on failure.
    """
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return None, None, ({'error': 'Guild not found'}, 404)

    try:
        current_user = bearer_client().get_current_user()
    except Exception:
        return None, None, ({'error': 'Not authenticated'}, 401)

    has_permission, level = check_guild_permission(guild, current_user.id)
    if not has_permission or level not in BILLING_PERMISSION_LEVELS:
        return None, None, ({'error': 'Permission denied'}, 403)

    doc = Guild.get(str(guild.id)).run()
    if doc is None:
        return None, None, ({'error': 'Guild config not found'}, 404)

    return guild, doc, None


def _resolve_customer(doc, current_user):
    """Return an existing Stripe customer for this guild/user, creating one if needed."""
    customer_id = (doc.premium or {}).get('customer')
    if customer_id:
        return customer_id

    email = getattr(current_user, 'email', None)
    if email:
        existing = stripe.Customer.list(email=email, limit=1).data
        if existing:
            return existing[0].id

    return stripe.Customer.create(
        email=email,
        name=getattr(current_user, 'username', None),
        metadata={'guild_id': str(doc.id), 'user_id': str(current_user.id)},
    ).id


# ── Checkout session ──────────────────────────────────────────────────────────
@stripe_bp.route('/<int:guild_id>/stripe/pay/<type>', methods=['POST'])
@login_required
async def stripe_pay(guild_id, type):
    if type not in premium_types:
        return {'error': 'Unknown premium plan'}, 400

    guild, doc, error = await asyncio.to_thread(_authorize_billing, guild_id)
    if error:
        return error

    current_user = bearer_client().get_current_user()
    return_url = url_for('dashboard.premium', _external=True, guild_id=guild.id)

    def _create_session():
        customer_id = _resolve_customer(doc, current_user)
        return stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': premium_types[type]['price_id'], 'quantity': 1}],
            mode=premium_types[type]['mode'],
            customer=customer_id,
            success_url=return_url + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=return_url,
            metadata={
                "guild_id": str(guild.id),
                "user_id": str(current_user.id),
                "plan": type,
            },
        )

    try:
        session = await asyncio.to_thread(_create_session)
    except stripe.error.StripeError:
        log.exception("Failed to create checkout session for guild %s", guild_id)
        return {'error': 'Could not start checkout'}, 502

    return {
        'checkout_session_id': session['id'],
        'checkout_public_key': current_app.config['STRIPE_PUBLIC_KEY'],
    }


# ── Billing portal ────────────────────────────────────────────────────────────
@stripe_bp.route('/<int:guild_id>/stripe/portal', methods=['POST'])
@login_required
async def stripe_portal(guild_id):
    guild, doc, error = await asyncio.to_thread(_authorize_billing, guild_id)
    if error:
        return error

    # The customer is read from the guild's own record — never from the request.
    customer_id = (doc.premium or {}).get('customer')
    if not customer_id:
        return {'error': 'No billing account for this guild'}, 404

    return_url = url_for('dashboard.premium', _external=True, guild_id=guild.id)

    def _create_portal():
        return stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )

    try:
        portal = await asyncio.to_thread(_create_portal)
    except stripe.error.StripeError:
        log.exception("Failed to create billing portal for guild %s", guild_id)
        return {'error': 'Could not open billing portal'}, 502

    return {'url': portal["url"], 'checkout_public_key': current_app.config['STRIPE_PUBLIC_KEY']}


# ── Webhook ───────────────────────────────────────────────────────────────────
def _claim_event(event) -> bool:
    """Record the event ID, returning False if it was already processed."""
    try:
        StripeEvent(id=event['id'], type=event['type']).insert()
    except DuplicateKeyError:
        return False
    return True


def _release_event(event_id):
    """Undo a claim so a Stripe retry of a failed event is processed again."""
    record = StripeEvent.get(event_id).run()
    if record:
        record.delete()


@stripe_bp.route('/webhook/stripe', methods=['POST'])
async def stripe_webhook():
    if request.content_length is not None and request.content_length > 1024 * 1024:
        return "REQUEST TOO BIG", 400

    payload = await request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = current_app.config["STRIPE_WEBHOOK_KEY"]

    if not sig_header:
        return {}, 400

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
    if not handler:
        return jsonify({"status": "ignored"}), 200

    if not await asyncio.to_thread(_claim_event, event):
        return jsonify({"status": "duplicate"}), 200

    try:
        return await asyncio.to_thread(handler, event['data']['object'])
    except Exception:
        # Drop the claim so Stripe's retry can be processed again.
        log.exception("Stripe webhook handler failed for event %s", event['id'])
        await asyncio.to_thread(_release_event, event['id'])
        return jsonify({"status": "error"}), 500


def _tz_from_doc(doc):
    try:
        return pytz.timezone(doc.settings.get('timezone') or 'UTC')
    except pytz.UnknownTimeZoneError:
        return pytz.UTC


def _utc(timestamp):
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _handle_checkout_completed(session):
    if not session:
        return {}, 400

    metadata = session.get('metadata') or {}
    guild_id = metadata.get('guild_id')
    user_id = metadata.get('user_id')
    if not guild_id or not user_id:
        log.warning("Checkout session %s is missing guild/user metadata", session.get('id'))
        return {"status": "ignored"}, 200

    doc = Guild.get(str(guild_id)).run()
    if not doc:
        return {"status": "ignored"}, 200

    mode = session.get('mode')
    payment_id = session.get('subscription') if mode == 'subscription' else session.get('payment_intent')
    if mode not in ('subscription', 'payment') or not payment_id:
        return {"status": "ignored"}, 200

    plan = metadata.get('plan')
    if plan not in premium_types:
        line_items = stripe.checkout.Session.list_line_items(session['id'], limit=1)
        description = (line_items['data'][0].get('description') or '') if line_items['data'] else ''
        plan = description.lower()

    doc.premium = {
        "id": payment_id,
        "status": True,
        "active": session.get('status') == 'complete',
        "plan": plan,
        "customer": session.get('customer'),
        "user_id": user_id,
        "subscribed_at": _utc(session["created"]).astimezone(_tz_from_doc(doc)),
    }
    doc.save()
    return {"status": "success"}, 200


def _find_guild_for_subscription(subscription_id, customer_id=None):
    """
    Look up the guild a subscription belongs to.

    The customer is checked too so a subscription can never flip the premium
    state of a guild it was not bought for.
    """
    doc = Guild.find_one({"premium.id": subscription_id}).run()
    if not doc:
        return None
    if customer_id and doc.premium.get('customer') not in (None, customer_id):
        log.warning("Subscription %s does not match customer on guild %s", subscription_id, doc.id)
        return None
    return doc


def _handle_subscription_updated(subscription):
    if not subscription or not subscription.get('id'):
        return {"error": "Invalid subscription data"}, 400

    doc = _find_guild_for_subscription(subscription['id'], subscription.get('customer'))
    if not doc:
        return {"status": "ignored"}, 200

    if subscription.get('cancel_at') or subscription.get('canceled_at'):
        doc.premium['status'] = False
        doc.premium['active'] = False
        doc.save()
        return {"status": "success", "msg": "User canceled subscription"}, 200

    if not doc.premium.get('status'):
        doc.premium['status'] = True
        doc.premium['active'] = True
        period_end = subscription.get('current_period_end')
        if period_end:
            doc.premium['subscribed_at'] = _utc(period_end).astimezone(_tz_from_doc(doc))
        doc.save()
        return {"status": "success", "msg": "User subscribed to premium"}, 200

    return {"status": "success"}, 200


def _handle_subscription_deleted(subscription):
    if not subscription or not subscription.get('id'):
        return {"error": "Invalid subscription data"}, 400

    doc = _find_guild_for_subscription(subscription['id'], subscription.get('customer'))
    if not doc:
        return {"status": "ignored"}, 200

    doc.premium['active'] = False
    doc.premium['status'] = False
    doc.save()
    return {"status": "success", "msg": "Subscription canceled"}, 200


def _handle_invoice_paid(invoice):
    subscription_id = invoice.get('subscription')
    if not subscription_id:
        return {"status": "ignored"}, 200

    doc = _find_guild_for_subscription(subscription_id, invoice.get('customer'))
    if not doc:
        return {"status": "ignored"}, 200

    subscription = stripe.Subscription.retrieve(subscription_id)
    items = subscription['items']['data']
    plan = (items[0]['price'].get('nickname') or '').lower() if items else doc.premium.get('plan')

    period_end = subscription.get('current_period_end')
    renewed_at = (
        _utc(period_end).astimezone(_tz_from_doc(doc)) if period_end
        else datetime.now(timezone.utc)
    )

    doc.premium = doc.premium | {
        "id": subscription_id,
        "status": True,
        "active": True,
        "plan": plan,
        "customer": subscription['customer'],
        "subscribed_at": renewed_at,
    }
    doc.save()

    return {"status": "success", "msg": "Invoice paid, subscription updated"}, 200


def _handle_invoice_payment_failed(invoice):
    subscription_id = invoice.get('subscription')
    if not subscription_id:
        return {"status": "ignored"}, 200

    doc = _find_guild_for_subscription(subscription_id, invoice.get('customer'))
    if not doc:
        return {"status": "ignored"}, 200

    doc.premium['active'] = False
    doc.premium['status'] = False
    doc.save()
    return {"status": "success", "msg": "Invoice payment failed"}, 200
