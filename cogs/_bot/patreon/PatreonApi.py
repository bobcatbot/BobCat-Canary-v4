import json
import aiohttp

class PatreonApi():
    def __init__(self, campaign_id=None, access_token=None):
        self.campaign_id = "8188764"
        self.access_token = "CeMP33TcR7N3uo0yvTSWywBEvG8ilCPSwSucI-6L6ys"

    async def fetch_all(self) -> dict:
        print("fetching patreons")
        """Get all discord id with current tiers of a patreon campaign
        :return: a dict that contain the discord id and the current tiers of the user
        :rtype: dict
        """        
        url = f'https://www.patreon.com/api/oauth2/v2/campaigns/{self.campaign_id}/members'
        params = {
            'include': 'user,currently_entitled_tiers',
            'fields[user]': 'social_connections',
        }

        headers = {'Authorization': f'Bearer {self.access_token}'} 
        patreons = {}

        end_cursor = False
        while not end_cursor:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    patreon_data = await response.json()
                    
                    for data in patreon_data['data']:
                        discord_user_id = None 
                        for patreon_user in patreon_data['included']:
                            if patreon_user['type'] != 'user':
                                continue
                            
                            if data['relationships']['user']['data']['id'] != patreon_user['id']:
                                continue 

                            patreon_user_data = patreon_user['attributes']
                            if not 'social_connections' in patreon_user_data:
                                continue

                            discord_data = patreon_user['attributes']['social_connections']['discord']
                        
                            if not discord_data or not 'user_id' in discord_data:
                                continue
          
                            discord_user_id = int(discord_data['user_id'])
                           
                        patreons[data['relationships']['user']['data']['id']] = { 
                            'tiers': [d['id'] for d in data['relationships']['currently_entitled_tiers']['data']],
                            'discord': discord_user_id
                        }

                    pagination_data = patreon_data['meta']['pagination']
                    if not pagination_data.get('cursors') or pagination_data['cursors']['next'] == None:
                        end_cursor = True
                    else:
                        next_cursor_id = pagination_data['cursors']['next']
                        params['page[cursor]'] = next_cursor_id

        return patreons

# usage example
# api = PatreonApi()
# all_patreons = asyncio.run(api.fetch_all())