import asyncio
import logging
import json
import pytz
import stripe
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from quart import Blueprint, current_app, jsonify, request, session, url_for

from ..consts import premium_types
from ..utils import bearer_client, check_guild_permission, login_required

from modules import bot as v
from modules.models import Guild, StripeEvent

# Configure logging
logger = logging.getLogger(__name__)

stripe_bp = Blueprint('stripe', __name__)

# Billing permission levels
BILLING_PERMISSION_LEVELS = ("Owner", "Administrator")


# ── Helper Functions ──────────────────────────────────────────────────────

def _authorize_billing(guild_id):
    """Resolve the guild for a billing request and authorize the session user."""
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


def _claim_event(event) -> bool:
    """Record the event ID, returning False if it was already processed."""
    try:
        StripeEvent(id=event['id'], type=event['type']).insert()
    except DuplicateKeyError:
        logger.info(f"Duplicate event {event['id']}, skipping")
        return False
    return True


def _release_event(event_id):
    """Undo a claim so a Stripe retry of a failed event is processed again."""
    record = StripeEvent.get(event_id).run()
    if record:
        record.delete()
        logger.info(f"Released claim for event {event_id}")


def _tz_from_doc(doc):
    """Get timezone from guild settings or default to UTC."""
    try:
        return pytz.timezone(doc.settings.get('timezone') or 'UTC')
    except (pytz.UnknownTimeZoneError, AttributeError):
        return pytz.UTC


def _utc(timestamp):
    """Convert timestamp to UTC datetime."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _find_guild_for_subscription(subscription_id, customer_id=None):
    """Look up the guild a subscription belongs to."""
    doc = Guild.find_one({"premium.id": subscription_id}).run()
    if not doc:
        return None
    doc_customer = doc.premium.get('customer')
    if customer_id and doc_customer and doc_customer != customer_id:
        logger.warning(f"Subscription {subscription_id} does not match customer on guild {doc.id}")
        return None
    return doc


def _get_stripe_metadata(obj):
    """
    Safely extract metadata from a Stripe object.
    Handles both StripeObject and dict types.
    """
    if not obj:
        return {}
    
    if isinstance(obj, dict):
        return obj.get('metadata', {})
    
    try:
        if hasattr(obj, 'metadata'):
            metadata = obj.metadata
            if hasattr(metadata, 'to_dict'):
                return metadata.to_dict()
            if isinstance(metadata, dict):
                return metadata
            try:
                return dict(metadata) if metadata else {}
            except:
                return {}
        
        if 'metadata' in obj:
            metadata = obj['metadata']
            if hasattr(metadata, 'to_dict'):
                return metadata.to_dict()
            if isinstance(metadata, dict):
                return metadata
            return {}
            
    except Exception as e:
        logger.warning(f"Error extracting metadata: {e}")
    
    return {}


# ── Webhook Handlers ──────────────────────────────────────────────────────

def _handle_checkout_completed(session):
    """Handle successful checkout session completion."""
    logger.info(f"Processing checkout.completed: {session.id}")
    
    if not session:
        logger.error("No session data")
        return {"error": "No session data"}, 400

    metadata = _get_stripe_metadata(session)
    logger.info(f"Extracted metadata: {metadata}")
    
    guild_id = metadata.get('guild_id')
    user_id = metadata.get('user_id')
    plan = metadata.get('plan')
    
    if not guild_id or not user_id:
        logger.warning(f"Missing metadata: guild_id={guild_id}, user_id={user_id}")
        return {"status": "ignored", "reason": "Missing metadata"}, 200

    doc = Guild.get(str(guild_id)).run()
    if not doc:
        logger.warning(f"Guild not found: {guild_id}")
        return {"status": "ignored", "reason": "Guild not found"}, 200

    mode = session.mode
    payment_id = session.subscription if mode == 'subscription' else session.payment_intent
    
    if mode not in ('subscription', 'payment') or not payment_id:
        logger.warning(f"Invalid mode or payment_id: mode={mode}, payment_id={payment_id}")
        return {"status": "ignored", "reason": "Invalid mode"}, 200

    current_period_end = None
    
    if mode == 'subscription' and session.subscription:
        try:
            subscription = stripe.Subscription.retrieve(session.subscription)
            logger.info(f"✅ Got subscription: {subscription.id}")
            
            if hasattr(subscription, 'items') and subscription.items:
                items = subscription.items
                if hasattr(items, 'data') and items.data:
                    subscription_item = items.data[0]
                    
                    if hasattr(subscription_item, 'current_period_end'):
                        current_period_end = subscription_item.current_period_end
                        logger.info(f"✅ Got period_end from items: {current_period_end}")
                        logger.info(f"✅ Period end date: {datetime.fromtimestamp(current_period_end)}")
                    else:
                        logger.warning("⚠️ No current_period_end found in subscription item")
                else:
                    logger.warning("⚠️ No data in subscription items")
            else:
                logger.warning("⚠️ No items found in subscription")
                
        except Exception as e:
            logger.error(f"Error retrieving subscription: {e}")

    if not plan or plan not in premium_types:
        try:
            line_items = stripe.checkout.Session.list_line_items(session.id, limit=1)
            if line_items['data']:
                description = line_items['data'][0].get('description') or ''
                for key in premium_types:
                    if key.lower() in description.lower():
                        plan = key
                        break
            if not plan:
                plan = 'basic'
        except Exception as e:
            logger.error(f"Error getting line items: {e}")
            plan = 'basic'

    doc.premium = {
        "id": payment_id,
        "status": True,
        "active": session.status == 'complete',
        "plan": plan,
        "customer": session.customer,
        "user_id": user_id,
        "period_end": _utc(current_period_end).astimezone(_tz_from_doc(doc)) if current_period_end else None,
    }
    doc.save()
    
    logger.info(f"✅ Premium activated for guild {guild_id} with plan {plan}")
    logger.info(f"📅 Stored period_end: {doc.premium.get('period_end')}")
    return {"status": "success", "guild_id": guild_id, "plan": plan}, 200


def _handle_subscription_updated(subscription):
    """Handle subscription updates."""
    if not subscription or not subscription.id:
        logger.error("Invalid subscription data")
        return {"error": "Invalid subscription data"}, 400

    doc = _find_guild_for_subscription(subscription.id, subscription.customer)
    if not doc:
        logger.info(f"No guild found for subscription {subscription.id}")
        return {"status": "ignored"}, 200

    if subscription.cancel_at or subscription.canceled_at:
        doc.premium = {}
        doc.save()
        logger.info(f"❌ Subscription cancelled for guild {doc.id}")
        return {"status": "success", "msg": "User canceled subscription"}, 200

    if not doc.premium.get('status'):
        doc.premium['status'] = True
        doc.premium['active'] = True

        if subscription.current_period_end:
            doc.premium['period_end'] = _utc(subscription.current_period_end).astimezone(_tz_from_doc(doc))

        doc.save()
        logger.info(f"✅ Subscription renewed for guild {doc.id}")
        return {"status": "success", "msg": "User subscribed to premium"}, 200

    return {"status": "success"}, 200


def _handle_subscription_deleted(subscription):
    """Handle subscription deletion."""
    if not subscription or not subscription.id:
        logger.error("Invalid subscription data")
        return {"error": "Invalid subscription data"}, 400

    doc = _find_guild_for_subscription(subscription.id, subscription.customer)
    if not doc:
        logger.info(f"No guild found for subscription {subscription.id}")
        return {"status": "ignored"}, 200

    doc.premium = {}
    doc.save()
    logger.info(f"❌ Subscription deleted for guild {doc.id}")
    return {"status": "success", "msg": "Subscription canceled"}, 200


def _handle_invoice_paid(invoice):
    """Handle successful invoice payment."""
    subscription_id = invoice.subscription
    if not subscription_id:
        logger.info("No subscription in invoice, ignoring")
        return {"status": "ignored"}, 200

    doc = _find_guild_for_subscription(subscription_id, invoice.customer)
    if not doc:
        logger.info(f"No guild found for subscription {subscription_id}")
        return {"status": "ignored"}, 200

    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        items = subscription['items']['data']
        plan = (items[0]['price'].get('nickname') or '').lower() if items else doc.premium.get('plan')
        if plan and plan not in premium_types:
            plan = doc.premium.get('plan', 'basic')

        period_end = subscription.current_period_end
        doc.premium.update({
            "id": subscription_id,
            "status": True,
            "active": True,
            "plan": plan,
            "customer": subscription.customer,
            "period_end": _utc(period_end).astimezone(_tz_from_doc(doc)) if period_end else None,
        })
        doc.save()
        logger.info(f"✅ Invoice paid for guild {doc.id}")
        return {"status": "success", "msg": "Invoice paid, subscription updated"}, 200
    except Exception as e:
        logger.error(f"Error handling invoice paid: {e}")
        return {"error": str(e)}, 500


def _handle_invoice_payment_failed(invoice):
    """Handle failed invoice payment."""
    subscription_id = invoice.subscription
    if not subscription_id:
        logger.info("No subscription in invoice, ignoring")
        return {"status": "ignored"}, 200

    doc = _find_guild_for_subscription(subscription_id, invoice.customer)
    if not doc:
        logger.info(f"No guild found for subscription {subscription_id}")
        return {"status": "ignored"}, 200

    doc.premium['active'] = False
    doc.premium['status'] = False
    doc.save()
    logger.warning(f"❌ Invoice payment failed for guild {doc.id}")
    return {"status": "success", "msg": "Invoice payment failed"}, 200


# ── Routes ─────────────────────────────────────────────────────────────────

@stripe_bp.route('/<int:guild_id>/stripe/pay/<type>', methods=['POST'])
@login_required
async def stripe_pay(guild_id, type):
    """Create a Stripe checkout session for premium purchase (Embedded modal method)."""
    if type not in premium_types:
        return jsonify({'error': 'Unknown premium plan'}), 400

    guild, doc, error = await asyncio.to_thread(_authorize_billing, guild_id)
    if error:
        return jsonify(error[0]), error[1]

    current_user = bearer_client().get_current_user()
    return_url = url_for('dashboard.premium', _external=True, guild_id=guild.id)

    def _create_session():
        customer_id = _resolve_customer(doc, current_user)
        return stripe.checkout.Session.create(
            line_items=[{
                'price': premium_types[type]['price_id'],
                'quantity': 1
            }],
            mode=premium_types[type]['mode'],
            customer=customer_id,
            ui_mode='elements',
            return_url=return_url + '?session_id={CHECKOUT_SESSION_ID}',
            metadata={
                "guild_id": str(guild.id),
                "user_id": str(current_user.id),
                "plan": type,
            },
        )

    try:
        session = await asyncio.to_thread(_create_session)
        logger.info(f"✅ Created checkout session {session.id}")
    except stripe.error.StripeError as e:
        logger.exception(f"Failed to create checkout session for guild {guild_id}")
        return jsonify({'error': str(e)}), 502

    return jsonify({
        'checkout_client_secret': session.client_secret,
        'checkout_public_key': current_app.config['STRIPE_PUBLIC_KEY'],
    }), 200


@stripe_bp.route('/<int:guild_id>/stripe/portal', methods=['POST'])
@login_required
async def stripe_portal(guild_id):
    """Create a Stripe billing portal session."""
    guild, doc, error = await asyncio.to_thread(_authorize_billing, guild_id)
    if error:
        return jsonify(error[0]), error[1]

    customer_id = (doc.premium or {}).get('customer')
    if not customer_id:
        return jsonify({'error': 'No billing account for this guild'}), 404

    return_url = url_for('dashboard.premium', _external=True, guild_id=guild.id)

    def _create_portal():
        return stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )

    try:
        portal = await asyncio.to_thread(_create_portal)
    except stripe.error.StripeError as e:
        logger.exception(f"Failed to create billing portal for guild {guild_id}")
        return jsonify({'error': str(e)}), 502

    return jsonify({'url': portal.url}), 200


@stripe_bp.route('/webhook/stripe', methods=['POST'])
async def stripe_webhook():
    """Handle Stripe webhook events."""
    logger.info("📨 Webhook received")
    
    if request.content_length and request.content_length > 1024 * 1024:
        logger.error("Request too big")
        return jsonify({"error": "Request too big"}), 400

    try:
        payload = await request.get_data()
    except Exception as e:
        logger.error(f"Failed to get payload: {e}")
        return jsonify({"error": "Failed to read payload"}), 400
    
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = current_app.config.get("STRIPE_WEBHOOK_KEY")
    
    if not endpoint_secret:
        logger.error("Webhook secret not configured")
        return jsonify({"error": "Webhook not configured"}), 500
    
    if not sig_header:
        logger.error("Missing Stripe signature header")
        return jsonify({"error": "Missing signature"}), 400

    event = None
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        logger.info(f"✅ Event verified: {event['type']} - {event['id']}")
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        if current_app.config.get("PY_ENV") != "production":
            logger.warning(f"⚠️ Signature verification failed, parsing directly (DEV MODE)")
            try:
                data = json.loads(payload.decode('utf-8'))
                event = stripe.Event.construct_from(data, stripe.api_key)
                logger.info(f"⚠️ Processing without verification: {event['type']} - {event['id']}")
            except Exception as parse_error:
                logger.error(f"Failed to parse payload: {parse_error}")
                return jsonify({"error": "Invalid payload"}), 400
        else:
            logger.error(f"Signature verification failed in production: {e}")
            return jsonify({"error": "Invalid signature"}), 400
    except Exception as e:
        logger.error(f"Unexpected error during verification: {e}")
        return jsonify({"error": "Verification error"}), 400

    if not event:
        logger.error("No event to process")
        return jsonify({"error": "No event"}), 400

    try:
        if not await asyncio.to_thread(_claim_event, event):
            logger.info(f"⏭️ Duplicate event {event['id']}, skipping")
            return jsonify({"status": "duplicate"}), 200
    except Exception as e:
        logger.error(f"Error claiming event: {e}")
        return jsonify({"error": "Database error"}), 500

    handlers = {
        'checkout.session.completed': _handle_checkout_completed,
        'customer.subscription.updated': _handle_subscription_updated,
        'customer.subscription.deleted': _handle_subscription_deleted,
        'invoice.paid': _handle_invoice_paid,
        'invoice.payment_failed': _handle_invoice_payment_failed,
    }

    handler = handlers.get(event['type'])
    if not handler:
        logger.info(f"⏭️ No handler for event type: {event['type']}")
        return jsonify({"status": "ignored"}), 200

    try:
        result = await asyncio.to_thread(handler, event['data']['object'])
        logger.info(f"✅ Handler completed for {event['type']}")
        
        if isinstance(result, tuple) and len(result) == 2:
            data, status = result
            if status >= 400:
                logger.error(f"Handler returned error: {data}")
                await asyncio.to_thread(_release_event, event['id'])
                return jsonify(data), status
            return jsonify(data), status
        
        return jsonify(result if isinstance(result, dict) else {"status": "success"}), 200
        
    except Exception as e:
        logger.exception(f"Handler failed for event {event['id']}: {e}")
        await asyncio.to_thread(_release_event, event['id'])
        return jsonify({"error": "Handler failed"}), 500


@stripe_bp.route('/webhook/stripe/health', methods=['GET'])
async def stripe_webhook_health():
    """Health check endpoint for webhook testing."""
    return jsonify({
        "status": "healthy",
        "endpoint": "/webhook/stripe",
        "config": {
            "secret_configured": bool(current_app.config.get("STRIPE_WEBHOOK_KEY")),
            "public_key_configured": bool(current_app.config.get("STRIPE_PUBLIC_KEY")),
            "environment": current_app.config.get("PY_ENV", "unknown"),
        }
    }), 200