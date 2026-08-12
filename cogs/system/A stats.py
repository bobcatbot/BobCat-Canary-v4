import discord
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
            "botCount": lambda s: s["members"]["bots"],
            "humanCount": lambda s: s["members"]["humans"],
            "onlineCount": lambda s: s["members"]["online"],
            "totalMembers": lambda s: s["members"]["total"],
            "textCount": lambda s: s["channels"]["text"],
            "voiceCount": lambda s: s["channels"]["voice"],
            "categoryCount": lambda s: s["channels"]["categories"],
            "totalChannels": lambda s: s["channels"]["total"],
            "roleCount": lambda s: s["roles"]["total"],
        }
        
        # Guilds flagged for refresh by event listeners
        self.dirty_guilds: set[int] = set()
        
        # Per-channel cooldown tracking (Discord allows ~2 name edits per 10 minutes)
        self.last_edit: Dict[int, datetime] = {}
        self.EDIT_COOLDOWN = timedelta(minutes=10)
        
        # Track if the loop is running
        self._loop_started = False

    # ── Event Listeners ──────────────────────────────────────────────────────
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Start the refresh loop when the bot is ready."""
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
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        """Mark guild as dirty when a channel is updated."""
        self.dirty_guilds.add(after.guild.id)

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
        
        # Count statuses
        online = 0
        idle = 0
        dnd = 0
        offline = 0
        
        for member in members:
            if member.bot:
                continue
            if member.status == discord.Status.online:
                online += 1
            elif member.status == discord.Status.idle:
                idle += 1
            elif member.status == discord.Status.dnd:
                dnd += 1
            else:
                offline += 1
        
        return {
            "members": {
                "total": len(members),
                "humans": sum(1 for m in members if not m.bot),
                "bots": sum(1 for m in members if m.bot),
                "online": online,
                "idle": idle,
                "dnd": dnd,
                "offline": offline,
            },
            "channels": {
                "total": len(guild.channels),
                "text": len(guild.text_channels),
                "voice": len(guild.voice_channels),
                "categories": len(guild.categories),
                "forums": len(guild.forums),
                "stage": len(guild.stage_channels),
            },
            "roles": {
                "total": len(guild.roles),
            },
            "emojis": {
                "total": len(guild.emojis),
                "animated": sum(1 for e in guild.emojis if e.animated),
                "static": sum(1 for e in guild.emojis if not e.animated),
            }
        }

    # ── Stats Update Logic ──────────────────────────────────────────────────
    
    async def update_guild_stats(self, guild: discord.Guild, force: bool = False) -> bool:
        """Update all stats channels for a guild.
        
        Args:
            guild: The guild to update
            force: If True, ignore cooldowns
            
        Returns:
            bool: True if any channels were updated
        """
        # Get guild config
        guild_doc: Guild = Guild.get(str(guild.id)).run()
        stats_config = guild_doc.dashboard.stats

        statsStatus = stats_config.get("status", False) 
        statsCounters = stats_config.get("counters", [])
        
        # Check if stats are enabled
        if not statsStatus:
            return False
            
        counters = statsCounters
        if not counters:
            return False
            
        stats = self.calculate_statistics(guild)
        now = datetime.now()
        updated = False
        
        for counter in counters:
            target = counter.get("target")
            handler = self.COUNTER_HANDLERS.get(target)
            
            if handler is None:
                continue
                
            channel_id = counter.get("channel_id")
            if not channel_id:
                continue
                
            try:
                channel_id_int = int(channel_id)
            except (TypeError, ValueError):
                continue
                
            channel = guild.get_channel(channel_id_int)
            if channel is None:
                continue
                
            # Check if the channel is a voice channel
            if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                continue
                
            # Respect cooldown unless forced
            last_edit = self.last_edit.get(channel.id)
            if not force and last_edit and (now - last_edit) < self.EDIT_COOLDOWN:
                continue
                
            try:
                count = handler(stats)
                text_template = counter.get("text", "{target}: {count}")
                
                # Replace placeholders
                new_name = text_template.format(
                    count=count,
                    target=target.replace("Count", "").lower(),
                    guild_name=guild.name[:20],  # Prevent too long names
                )
                
                # Discord voice channel name limit is 100 characters
                if len(new_name) > 100:
                    new_name = new_name[:97] + "..."
                    
                if channel.name != new_name:
                    await channel.edit(name=new_name, reason="Stats update")
                    self.last_edit[channel.id] = now
                    updated = True
                    
            except (discord.Forbidden, discord.HTTPException) as e:
                # Log but continue with other channels
                print(f"Failed to update stats channel {channel.id} in {guild.id}: {e}")
                continue
                
        # Update the counter cache in the database
        if updated:
            # Update the stored counts
            for counter in counters:
                target = counter.get("target")
                handler = self.COUNTER_HANDLERS.get(target)
                if handler:
                    counter["count"] = handler(stats)
                    
            # Save the updated config
            guild_doc.dashboard.stats["counters"] = counters
            guild_doc.updated_at = discord.utils.utcnow()
            guild_doc.save()
            
        return updated

    # ── Background Task ─────────────────────────────────────────────────────
    
    @tasks.loop(minutes=1)
    async def refresh_loop(self):
        """Periodically refresh stats for all guilds."""
        # Get dirty guilds that need immediate updates
        dirty = self.dirty_guilds.copy()
        self.dirty_guilds.clear()
        
        # Update dirty guilds first
        for guild in self.client.guilds:
            if guild.id in dirty:
                await self.update_guild_stats(guild, force=True)
                
        # Then update all guilds (respecting cooldowns)
        for guild in self.client.guilds:
            await self.update_guild_stats(guild, force=False)

    @refresh_loop.before_loop
    async def before_refresh_loop(self):
        """Wait for the bot to be ready before starting the loop."""
        await self.client.wait_until_ready()

def setup(client):
    client.add_cog(Stats(client))