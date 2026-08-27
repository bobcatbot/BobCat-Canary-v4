import discord
import random
from typing import Dict
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from modules import bot as v
from modules.models import Guild

class Stats(commands.Cog):
    """Automatic server statistics voice channels.
    
    Creates voice channels that display real-time server statistics:
    - Total members
    - Online members
    - Text/Voice channels
    - Roles count
    - Bots vs Humans
    """
    def __init__(self, client: commands.Bot):
        self.client = client
        
        # Counter definitions - maps config target to function
        self.COUNTER_HANDLERS = {
            "bots": lambda s: s["members"]["bots"],
            "humans": lambda s: s["members"]["humans"],
            "onlineMembers": lambda s: s["members"]["online"],
            "totalMembers": lambda s: s["members"]["total"],
            "textChannels": lambda s: s["channels"]["text"],
            "voiceChannels": lambda s: s["channels"]["voice"],
            "category": lambda s: s["channels"]["categories"],
            "totalChannels": lambda s: s["channels"]["total"],
            "roles": lambda s: s["roles"]["total"],
        }
        
        # Guilds flagged for refresh by event listeners
        self.dirty_guilds: set[int] = set()
        
        # Per-channel cooldown tracking
        self.last_edit: Dict[int, datetime] = {}
        self.EDIT_COOLDOWN = timedelta(minutes=15)  # ⬆️ Increased from 10 to 15 minutes
        
        # Track failed edits to back off further
        self.failed_edits: Dict[int, int] = {}  # channel_id -> failure count
        self.max_failures = 3
        
        self._loop_started = False

    # ── Event Listeners ──────────────────────────────────────────────────────
    
    @commands.Cog.listener()
    async def on_ready(self):
        if not self._loop_started:
            self.refresh_loop.start()
            self._loop_started = True

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Mark guild as dirty when a member joins."""
        if not member.bot:
            self.dirty_guilds.add(member.guild.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Mark guild as dirty when a member leaves."""
        self.dirty_guilds.add(member.guild.id)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Mark guild as dirty when a member's status changes."""
        if before.status != after.status:
            self.dirty_guilds.add(after.guild.id)

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        """Mark guild as dirty when a member's presence changes."""
        if before.status != after.status:
            self.dirty_guilds.add(after.guild.id)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Mark guild as dirty when a channel is created."""
        self.dirty_guilds.add(channel.guild.id)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Mark guild as dirty when a channel is deleted."""
        self.dirty_guilds.add(channel.guild.id)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Mark guild as dirty when a role is created."""
        self.dirty_guilds.add(role.guild.id)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Mark guild as dirty when a role is deleted."""
        self.dirty_guilds.add(role.guild.id)

    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        self.refresh_loop.cancel()
        self._loop_started = False

    # ── Statistics Calculation ──────────────────────────────────────────────
    
    def calculate_statistics(self, guild: discord.Guild) -> dict:
        """Calculate all statistics for a guild."""
        members = guild.members
        return {
            "members": {
                "total": len(members),
                "humans": sum(1 for m in members if not m.bot),
                "bots": sum(1 for m in members if m.bot),
                "online": sum(1 for m in members if not m.bot and m.status != discord.Status.offline),
            },
            "channels": {
                "total": len(guild.channels),
                "text": len(guild.text_channels),
                "voice": len(guild.voice_channels),
                "categories": len(guild.categories),
            },
            "roles": {
                "total": len(guild.roles),
            }
        }

    # ── Stats Update Logic ──────────────────────────────────────────────────
    
    async def update_guild_stats(self, guild: discord.Guild, force: bool = False) -> bool:
        """Update all stats channels for a guild."""
        guild_doc = await Guild.get(str(guild.id))
        if guild_doc is None:
            return False
        
        stats_config = guild_doc.dashboard.stats
        statsStatus = stats_config.get('status', False)
        statsCounters = stats_config.get('counters', [])
        
        if not statsStatus:
            return False
        if not statsCounters:
            return False
        
        stats = self.calculate_statistics(guild)
        now = datetime.now()
        updated = False
        
        for counter in statsCounters:
            target = counter.get("target")
            channel_id = counter.get("channel_id")
            handler = self.COUNTER_HANDLERS.get(target)
            
            if handler is None:
                continue
            
            if not channel_id:
                continue
            
            try:
                channel_id_int = int(channel_id)
            except (TypeError, ValueError):
                continue
            
            channel = guild.get_channel(channel_id_int)
            if channel is None:
                continue
            
            if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                continue
            
            # Check if this channel has been failing
            failures = self.failed_edits.get(channel.id, 0)
            if failures >= self.max_failures:
                # Skip updating this channel until next restart
                continue
            
            # Check cooldown
            last_edit = self.last_edit.get(channel.id)
            if not force and last_edit and (now - last_edit) < self.EDIT_COOLDOWN:
                continue
            
            try:
                count = handler(stats)
                text_template = counter.get("text", "{kind}: {count}")
                
                new_name = text_template.format(
                    kind=target.replace("Count", "").lower(),
                    count=count,
                )
                
                if len(new_name) > 100:
                    new_name = new_name[:97] + "..."
                
                if channel.name != new_name:
                    await channel.edit(name=new_name, reason="Stats update")
                    self.last_edit[channel.id] = now
                    # Reset failures on success
                    self.failed_edits[channel.id] = 0
                    updated = True
            except discord.Forbidden:
                # Don't have permission to edit
                self.failed_edits[channel.id] = failures + 1
                print(f"⚠️ Missing permission to edit stats channel {channel.name} in {guild.name}")
                continue
            except discord.HTTPException as e:
                # Rate limited or other error
                self.failed_edits[channel.id] = failures + 1
                if "rate limited" in str(e).lower():
                    print(f"⏳ Rate limited on stats channel {channel.name}, backing off...")
                continue
        
        # Update stored counts
        if updated:
            for counter in statsCounters:
                target = counter.get("target")
                handler = self.COUNTER_HANDLERS.get(target)
                if handler:
                    counter["count"] = handler(stats)
                    
            current_stats = getattr(guild_doc.dashboard, "stats", {})
            current_stats["counters"] = statsCounters
            guild_doc.dashboard.stats = current_stats
            guild_doc.updated_at = discord.utils.utcnow()
            await guild_doc.save()
        
        return updated

    # ── Background Task ─────────────────────────────────────────────────────
    
    @tasks.loop(minutes=10)
    async def refresh_loop(self):
        for guild in self.client.guilds:
            await self.update_guild_stats(guild, force=False)
            await discord.utils.sleep_until(datetime.now() + timedelta(seconds=random.uniform(1, 2)))

    @refresh_loop.before_loop
    async def before_refresh_loop(self):
        await self.client.wait_until_ready()

def setup(client):
    client.add_cog(Stats(client))