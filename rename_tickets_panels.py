import pymongo
from dotenv import load_dotenv
import os

load_dotenv()

mongoURI = os.getenv('mongoURI_db')
client = pymongo.MongoClient(mongoURI)
db = client['Bot']['Bot']

def rename_pannel_to_panel():
    docs = db.find({})
    updated = 0
    skipped = 0

    for doc in docs:
        guild_id = doc.get('_id')
        bot_data = doc.get('Bot', {})
        dash_data = doc.get('Dash', {})
        changed = False

        # ── Bot.tickets: pannelid ──────────────────────────────────────────
        tickets = bot_data.get('tickets', [])
        for ticket in tickets:
            if 'pannelid' in ticket:
                ticket['panelid'] = ticket.pop('pannelid')
                changed = True

        # ── Dash.ticketing: pannels ────────────────────────────────────────
        ticketing = dash_data.get('ticketing', {})
        pannels = ticketing.get('pannels', [])
        if pannels:
            ticketing['panels'] = ticketing.pop('pannels')
            changed = True

        if not changed:
            print(f"[SKIP] {guild_id} — nothing to change")
            skipped += 1
            continue

        db.update_one(
            {'_id': guild_id},
            {'$set': {
                'Bot.tickets': tickets,
                'Dash.ticketing': ticketing,
            }}
        )
        print(f"[OK] {guild_id} — updated")
        updated += 1

    print(f"\nDone. {updated} updated, {skipped} skipped.")

if __name__ == '__main__':
    rename_pannel_to_panel()