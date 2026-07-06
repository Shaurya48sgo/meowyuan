import aiosqlite
import json
import os
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "meowyuan.db")


class Database:
    def __init__(self):
        self.db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        self.db = await aiosqlite.connect(DB_PATH)
        self.db.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        if self.db:
            await self.db.close()

    async def _create_tables(self):
        await self.db.executescript("""
            CREATE TABLE IF NOT EXISTS global_config (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS global_devs (
                user_id INTEGER PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER,
                key TEXT,
                value TEXT,
                PRIMARY KEY (guild_id, key)
            );

            CREATE TABLE IF NOT EXISTS users (
                guild_id INTEGER,
                user_id INTEGER,
                currency TEXT,
                balance REAL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, currency)
            );

            CREATE TABLE IF NOT EXISTS user_inventory (
                guild_id INTEGER,
                user_id INTEGER,
                item_name TEXT,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, item_name)
            );

            CREATE TABLE IF NOT EXISTS card_slots (
                guild_id INTEGER,
                user_id INTEGER,
                slot_type TEXT,
                slot_num INTEGER,
                item_name TEXT,
                expires_at REAL,
                PRIMARY KEY (guild_id, user_id, slot_type, slot_num)
            );

            CREATE TABLE IF NOT EXISTS shop_items (
                guild_id INTEGER,
                currency TEXT,
                item_name TEXT,
                price REAL,
                stock INTEGER,
                description TEXT,
                emoji TEXT,
                default_stock INTEGER,
                auto_refill_interval TEXT,
                auto_refill_amount INTEGER,
                PRIMARY KEY (guild_id, currency, item_name)
            );

            CREATE TABLE IF NOT EXISTS gift_config (
                guild_id INTEGER,
                currency TEXT,
                item_name TEXT,
                chance REAL,
                PRIMARY KEY (guild_id, currency, item_name)
            );

            CREATE TABLE IF NOT EXISTS unclaimed_gifts (
                guild_id INTEGER,
                user_id INTEGER,
                item_name TEXT,
                quantity INTEGER,
                expires_at REAL,
                id INTEGER PRIMARY KEY AUTOINCREMENT
            );

            CREATE TABLE IF NOT EXISTS auto_gifts (
                guild_id INTEGER,
                role_id INTEGER,
                currency TEXT,
                item_name TEXT,
                amount INTEGER,
                interval_seconds INTEGER,
                blacklist_role_id INTEGER,
                id INTEGER PRIMARY KEY AUTOINCREMENT
            );

            CREATE TABLE IF NOT EXISTS punishments (
                guild_id INTEGER,
                user_id INTEGER,
                punishment_type TEXT,
                reason TEXT,
                mod_id INTEGER,
                created_at REAL,
                expires_at REAL,
                role_id INTEGER,
                id INTEGER PRIMARY KEY AUTOINCREMENT
            );

            CREATE TABLE IF NOT EXISTS warns (
                guild_id INTEGER,
                user_id INTEGER,
                reason TEXT,
                mod_id INTEGER,
                created_at REAL,
                id INTEGER PRIMARY KEY AUTOINCREMENT
            );

            CREATE TABLE IF NOT EXISTS jail_config (
                guild_id INTEGER PRIMARY KEY,
                silence_role_id INTEGER,
                log_channel_id INTEGER,
                role_order TEXT,
                role_order_enabled INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS full_reverse_immunity_roles (
                guild_id INTEGER,
                role_id INTEGER,
                custom_message TEXT,
                gif_url TEXT,
                PRIMARY KEY (guild_id, role_id)
            );

            CREATE TABLE IF NOT EXISTS full_immunity_roles (
                guild_id INTEGER,
                role_id INTEGER,
                PRIMARY KEY (guild_id, role_id)
            );

            CREATE TABLE IF NOT EXISTS power_users (
                guild_id INTEGER,
                user_id INTEGER,
                power_type TEXT,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS power_roles (
                guild_id INTEGER,
                role_id INTEGER,
                PRIMARY KEY (guild_id, role_id)
            );

            CREATE TABLE IF NOT EXISTS icon_role_mappings (
                guild_id INTEGER,
                role_id INTEGER,
                icon_role_id INTEGER,
                PRIMARY KEY (guild_id, role_id)
            );

            CREATE TABLE IF NOT EXISTS icon_roles (
                guild_id INTEGER,
                role_id INTEGER,
                PRIMARY KEY (guild_id, role_id)
            );

            CREATE TABLE IF NOT EXISTS reaction_role_messages (
                guild_id INTEGER,
                channel_id INTEGER,
                message_id INTEGER,
                title TEXT,
                PRIMARY KEY (guild_id, message_id)
            );

            CREATE TABLE IF NOT EXISTS reaction_role_entries (
                guild_id INTEGER,
                message_id INTEGER,
                role_id INTEGER,
                emoji TEXT,
                PRIMARY KEY (guild_id, message_id, role_id)
            );

            CREATE TABLE IF NOT EXISTS group_reaction_roles (
                guild_id INTEGER,
                group_name TEXT,
                max_roles INTEGER,
                PRIMARY KEY (guild_id, group_name)
            );

            CREATE TABLE IF NOT EXISTS grr_roles (
                guild_id INTEGER,
                group_name TEXT,
                role_id INTEGER,
                emoji TEXT,
                PRIMARY KEY (guild_id, group_name, role_id)
            );

            CREATE TABLE IF NOT EXISTS grr_ignore_roles (
                guild_id INTEGER,
                group_name TEXT,
                role_id INTEGER,
                PRIMARY KEY (guild_id, group_name, role_id)
            );

            CREATE TABLE IF NOT EXISTS grr_required_roles (
                guild_id INTEGER,
                group_name TEXT,
                role_id INTEGER,
                PRIMARY KEY (guild_id, group_name, role_id)
            );

            CREATE TABLE IF NOT EXISTS custom_roles (
                guild_id INTEGER,
                user_id INTEGER,
                role_id INTEGER,
                name TEXT,
                color TEXT,
                id INTEGER PRIMARY KEY AUTOINCREMENT
            );

            CREATE TABLE IF NOT EXISTS active_custom_role (
                guild_id INTEGER,
                user_id INTEGER,
                role_id INTEGER,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS conversion_tracking (
                guild_id INTEGER,
                user_id INTEGER,
                week_start REAL,
                amount_converted REAL,
                PRIMARY KEY (guild_id, user_id, week_start)
            );

            CREATE TABLE IF NOT EXISTS transfer_tracking (
                guild_id INTEGER,
                user_id INTEGER,
                currency TEXT,
                week_start REAL,
                amount_sent REAL,
                PRIMARY KEY (guild_id, user_id, currency, week_start)
            );

            CREATE TABLE IF NOT EXISTS merged_accounts (
                guild_id INTEGER,
                primary_id INTEGER,
                secondary_id INTEGER,
                name TEXT,
                PRIMARY KEY (guild_id, primary_id, secondary_id)
            );

            CREATE TABLE IF NOT EXISTS log_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                log_type TEXT,
                data TEXT,
                created_at REAL
            );

            CREATE TABLE IF NOT EXISTS jail_state (
                guild_id INTEGER,
                user_id INTEGER,
                jailed_until REAL,
                jailer_id INTEGER,
                is_pro INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS strike_tracking (
                guild_id INTEGER,
                user_id INTEGER,
                strike_count INTEGER DEFAULT 0,
                full_immunity_until REAL,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS themes (
                name TEXT PRIMARY KEY,
                is_active INTEGER DEFAULT 0,
                prefixes TEXT DEFAULT '[]',
                currency_name TEXT,
                currency_emoji TEXT
            );

            CREATE TABLE IF NOT EXISTS hecker_users (
                guild_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS infinity_users (
                user_id INTEGER PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS dev_config (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS play_gif_commands (
                name TEXT PRIMARY KEY,
                data TEXT
            );

            CREATE TABLE IF NOT EXISTS jail_gifs (
                case_type INTEGER,
                url TEXT,
                id INTEGER PRIMARY KEY AUTOINCREMENT
            );

            CREATE TABLE IF NOT EXISTS jail_messages (
                guild_id INTEGER,
                case_type TEXT,
                message TEXT,
                PRIMARY KEY (guild_id, case_type)
            );

            CREATE TABLE IF NOT EXISTS earned_reactions (
                guild_id INTEGER,
                user_id INTEGER,
                message_id INTEGER,
                PRIMARY KEY (guild_id, user_id, message_id)
            );

            CREATE TABLE IF NOT EXISTS earned_invites (
                guild_id INTEGER,
                user_id INTEGER,
                invite_code TEXT,
                PRIMARY KEY (guild_id, user_id, invite_code)
            );

            CREATE TABLE IF NOT EXISTS punishment_config (
                guild_id INTEGER PRIMARY KEY,
                mod_logs_channel_id INTEGER,
                reports_channel_id INTEGER,
                mod_roles TEXT DEFAULT '[]',
                role_punishments TEXT DEFAULT '{}',
                standard_punishments TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS economy_config (
                guild_id INTEGER PRIMARY KEY,
                data TEXT
            );

            CREATE TABLE IF NOT EXISTS earning_blacklist_channels (
                guild_id INTEGER,
                earning_type TEXT,
                channel_id INTEGER,
                PRIMARY KEY (guild_id, earning_type, channel_id)
            );

            CREATE TABLE IF NOT EXISTS earning_blacklist_roles (
                guild_id INTEGER,
                earning_type TEXT,
                role_id INTEGER,
                PRIMARY KEY (guild_id, earning_type, role_id)
            );

            CREATE TABLE IF NOT EXISTS boost_config (
                guild_id INTEGER,
                currency TEXT,
                earning_type TEXT,
                boost_type TEXT,
                target_id INTEGER,
                target_type TEXT,
                percentage REAL,
                id INTEGER PRIMARY KEY AUTOINCREMENT
            );

            CREATE TABLE IF NOT EXISTS earned_vc (
                guild_id INTEGER,
                user_id INTEGER,
                last_minute INTEGER,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS temp_role_assignments (
                guild_id INTEGER,
                user_id INTEGER,
                role_id INTEGER,
                expires_at REAL,
                PRIMARY KEY (guild_id, user_id, role_id)
            );
        """)
        await self.db.commit()

    async def get_global_config(self, key: str, default=None):
        cursor = await self.db.execute("SELECT value FROM global_config WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return json.loads(row[0]) if row else default

    async def set_global_config(self, key: str, value):
        await self.db.execute("INSERT OR REPLACE INTO global_config (key, value) VALUES (?, ?)",
                             (key, json.dumps(value)))
        await self.db.commit()

    async def get_guild_config(self, guild_id: int, key: str, default=None):
        cursor = await self.db.execute("SELECT value FROM guild_config WHERE guild_id = ? AND key = ?",
                                      (guild_id, key))
        row = await cursor.fetchone()
        return json.loads(row[0]) if row else default

    async def set_guild_config(self, guild_id: int, key: str, value):
        await self.db.execute("INSERT OR REPLACE INTO guild_config (guild_id, key, value) VALUES (?, ?, ?)",
                             (guild_id, key, json.dumps(value)))
        await self.db.commit()

    async def del_guild_config(self, guild_id: int, key: str):
        await self.db.execute("DELETE FROM guild_config WHERE guild_id = ? AND key = ?", (guild_id, key))
        await self.db.commit()

    async def get_user_balance(self, guild_id: int, user_id: int, currency: str) -> float:
        cursor = await self.db.execute(
            "SELECT balance FROM users WHERE guild_id = ? AND user_id = ? AND currency = ?",
            (guild_id, user_id, currency))
        row = await cursor.fetchone()
        return row[0] if row else 0.0

    async def set_user_balance(self, guild_id: int, user_id: int, currency: str, balance: float):
        await self.db.execute(
            "INSERT OR REPLACE INTO users (guild_id, user_id, currency, balance) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, currency, balance))
        await self.db.commit()

    async def add_user_balance(self, guild_id: int, user_id: int, currency: str, amount: float):
        current = await self.get_user_balance(guild_id, user_id, currency)
        await self.set_user_balance(guild_id, user_id, currency, current + amount)

    async def get_inventory(self, guild_id: int, user_id: int) -> dict:
        cursor = await self.db.execute(
            "SELECT item_name, quantity FROM user_inventory WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id))
        return {row[0]: row[1] for row in await cursor.fetchall()}

    async def add_inventory(self, guild_id: int, user_id: int, item: str, qty: int = 1):
        await self.db.execute(
            "INSERT OR REPLACE INTO user_inventory (guild_id, user_id, item_name, quantity) VALUES (?, ?, ?, "
            "COALESCE((SELECT quantity FROM user_inventory WHERE guild_id = ? AND user_id = ? AND item_name = ?), 0) + ?)",
            (guild_id, user_id, item, guild_id, user_id, item, qty))
        await self.db.commit()

    async def remove_inventory(self, guild_id: int, user_id: int, item: str, qty: int = 1):
        current = await self.get_inventory(guild_id, user_id)
        if current.get(item, 0) < qty:
            return False
        await self.db.execute(
            "UPDATE user_inventory SET quantity = quantity - ? WHERE guild_id = ? AND user_id = ? AND item_name = ?",
            (qty, guild_id, user_id, item))
        await self.db.commit()
        return True

    async def is_global_dev(self, user_id: int) -> bool:
        cursor = await self.db.execute("SELECT 1 FROM global_devs WHERE user_id = ?", (user_id,))
        return await cursor.fetchone() is not None

    async def add_global_dev(self, user_id: int):
        await self.db.execute("INSERT OR IGNORE INTO global_devs (user_id) VALUES (?)", (user_id,))
        await self.db.commit()

    async def remove_global_dev(self, user_id: int):
        await self.db.execute("DELETE FROM global_devs WHERE user_id = ?", (user_id,))
        await self.db.commit()

    async def list_global_devs(self) -> list:
        cursor = await self.db.execute("SELECT user_id FROM global_devs")
        return [row[0] for row in await cursor.fetchall()]

    async def is_infinity(self, user_id: int) -> bool:
        cursor = await self.db.execute("SELECT 1 FROM infinity_users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone() is not None

    async def set_infinity(self, user_id: int, value: bool):
        if value:
            await self.db.execute("INSERT OR IGNORE INTO infinity_users (user_id) VALUES (?)", (user_id,))
        else:
            await self.db.execute("DELETE FROM infinity_users WHERE user_id = ?", (user_id,))
        await self.db.commit()

    async def is_hecker(self, guild_id: int, user_id: int) -> bool:
        cursor = await self.db.execute("SELECT 1 FROM hecker_users WHERE guild_id = ? AND user_id = ?",
                                      (guild_id, user_id))
        return await cursor.fetchone() is not None

    async def set_hecker(self, guild_id: int, user_id: int, value: bool):
        if value:
            await self.db.execute("INSERT OR IGNORE INTO hecker_users (guild_id, user_id) VALUES (?, ?)",
                                (guild_id, user_id))
        else:
            await self.db.execute("DELETE FROM hecker_users WHERE guild_id = ? AND user_id = ?",
                                (guild_id, user_id))
        await self.db.commit()

    async def has_power(self, guild_id: int, user_id: int) -> bool:
        cursor = await self.db.execute(
            "SELECT 1 FROM power_users WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        return await cursor.fetchone() is not None

    async def has_spower(self, guild_id: int, user_id: int) -> bool:
        cursor = await self.db.execute(
            "SELECT 1 FROM power_users WHERE guild_id = ? AND user_id = ? AND power_type = 'spower'",
            (guild_id, user_id))
        return await cursor.fetchone() is not None

    async def set_power(self, guild_id: int, user_id: int, power_type: str, value: bool):
        if value:
            await self.db.execute(
                "INSERT OR REPLACE INTO power_users (guild_id, user_id, power_type) VALUES (?, ?, ?)",
                (guild_id, user_id, power_type))
        else:
            await self.db.execute("DELETE FROM power_users WHERE guild_id = ? AND user_id = ?",
                                (guild_id, user_id))
        await self.db.commit()

    async def get_shop_items(self, guild_id: int, currency: str) -> list:
        cursor = await self.db.execute(
            "SELECT item_name, price, stock, description, emoji, default_stock, auto_refill_interval, auto_refill_amount "
            "FROM shop_items WHERE guild_id = ? AND currency = ? ORDER BY rowid", (guild_id, currency))
        return [dict(row) for row in await cursor.fetchall()]

    async def log_entry(self, guild_id: int, log_type: str, data: dict):
        import time
        await self.db.execute(
            "INSERT INTO log_entries (guild_id, log_type, data, created_at) VALUES (?, ?, ?, ?)",
            (guild_id, log_type, json.dumps(data), time.time()))
        await self.db.commit()

    async def get_logs(self, guild_id: int, log_type: str = None, limit: int = 50):
        if log_type:
            cursor = await self.db.execute(
                "SELECT data, created_at FROM log_entries WHERE guild_id = ? AND log_type = ? ORDER BY created_at DESC LIMIT ?",
                (guild_id, log_type, limit))
        else:
            cursor = await self.db.execute(
                "SELECT data, created_at FROM log_entries WHERE guild_id = ? ORDER BY created_at DESC LIMIT ?",
                (guild_id, limit))
        return [{"data": json.loads(row[0]), "created_at": row[1]} for row in await cursor.fetchall()]

    async def reset_guild(self, guild_id: int):
        tables = ["guild_config", "users", "user_inventory", "card_slots", "shop_items", "gift_config",
                  "unclaimed_gifts", "auto_gifts", "punishments", "warns", "jail_config",
                  "full_reverse_immunity_roles", "full_immunity_roles", "power_users", "power_roles",
                  "icon_role_mappings", "icon_roles", "reaction_role_messages", "reaction_role_entries",
                  "group_reaction_roles", "grr_roles", "grr_ignore_roles", "grr_required_roles",
                  "custom_roles", "active_custom_role", "conversion_tracking", "transfer_tracking",
                  "merged_accounts", "log_entries", "jail_state", "strike_tracking", "hecker_users",
                  "jail_messages", "earned_reactions", "earned_invites", "punishment_config",
                  "economy_config", "earning_blacklist_channels", "earning_blacklist_roles",
                  "boost_config", "earned_vc", "temp_role_assignments"]
        for table in tables:
            await self.db.execute(f"DELETE FROM {table} WHERE guild_id = ?", (guild_id,))
        await self.db.commit()

    async def get_jail_state(self, guild_id: int, user_id: int):
        cursor = await self.db.execute(
            "SELECT jailed_until, jailer_id, is_pro FROM jail_state WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id))
        return await cursor.fetchone()

    async def set_jail_state(self, guild_id: int, user_id: int, jailed_until: float, jailer_id: int, is_pro: int = 0):
        await self.db.execute(
            "INSERT OR REPLACE INTO jail_state (guild_id, user_id, jailed_until, jailer_id, is_pro) VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, jailed_until, jailer_id, is_pro))
        await self.db.commit()

    async def remove_jail_state(self, guild_id: int, user_id: int):
        await self.db.execute("DELETE FROM jail_state WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await self.db.commit()

    async def get_strike_tracking(self, guild_id: int, user_id: int):
        cursor = await self.db.execute(
            "SELECT strike_count, full_immunity_until FROM strike_tracking WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id))
        return await cursor.fetchone()

    async def increment_strike(self, guild_id: int, user_id: int):
        import time
        current = await self.get_strike_tracking(guild_id, user_id)
        count = (current[0] if current else 0) + 1
        fi_until = current[1] if current else None
        if count >= 3:
            fi_until = time.time() + 43200
            count = 0
        await self.db.execute(
            "INSERT OR REPLACE INTO strike_tracking (guild_id, user_id, strike_count, full_immunity_until) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, count, fi_until or 0))
        await self.db.commit()
        return count >= 3, fi_until

    async def theme_exists(self, name: str) -> bool:
        cursor = await self.db.execute("SELECT 1 FROM themes WHERE name = ?", (name,))
        return await cursor.fetchone() is not None

    async def create_theme(self, name: str, prefixes: list, currency_name: str = None, currency_emoji: str = None):
        await self.db.execute(
            "INSERT OR REPLACE INTO themes (name, prefixes, currency_name, currency_emoji) VALUES (?, ?, ?, ?)",
            (name, json.dumps(prefixes), currency_name, currency_emoji))
        await self.db.commit()

    async def get_active_theme(self):
        cursor = await self.db.execute("SELECT * FROM themes WHERE is_active = 1")
        return await cursor.fetchone()

    async def set_active_theme(self, name: str):
        await self.db.execute("UPDATE themes SET is_active = 0")
        await self.db.execute("UPDATE themes SET is_active = 1 WHERE name = ?", (name,))
        await self.db.commit()

    async def delete_theme(self, name: str):
        await self.db.execute("DELETE FROM themes WHERE name = ?", (name,))
        await self.db.commit()

    async def get_all_themes(self):
        cursor = await self.db.execute("SELECT * FROM themes")
        return await cursor.fetchall()

    async def get_prefixes(self):
        theme = await self.get_active_theme()
        if theme:
            prefixes = json.loads(theme["prefixes"])
            return prefixes if prefixes else ["meow"]
        return ["meow"]

    async def add_prefix(self, theme_name: str, prefix: str):
        cursor = await self.db.execute("SELECT prefixes FROM themes WHERE name = ?", (theme_name,))
        row = await cursor.fetchone()
        if row:
            prefixes = json.loads(row[0])
            if prefix not in prefixes:
                prefixes.append(prefix)
            await self.db.execute("UPDATE themes SET prefixes = ? WHERE name = ?",
                                (json.dumps(prefixes), theme_name))
            await self.db.commit()

    async def remove_prefix(self, theme_name: str, prefix: str):
        cursor = await self.db.execute("SELECT prefixes FROM themes WHERE name = ?", (theme_name,))
        row = await cursor.fetchone()
        if row:
            prefixes = json.loads(row[0])
            if prefix in prefixes:
                prefixes.remove(prefix)
            await self.db.execute("UPDATE themes SET prefixes = ? WHERE name = ?",
                                (json.dumps(prefixes), theme_name))
            await self.db.commit()

    async def ensure_user(self, guild_id: int, user_id: int):
        cursors = await self.db.execute(
            "SELECT currency FROM economy_config WHERE guild_id = ?", (guild_id,))
        config_row = await cursors.fetchone()
        if not config_row:
            return
        config = json.loads(config_row[0])
        currencies = config.get("currencies", {})
        initial = config.get("initial_capital", {})
        for name, emoji in currencies.items():
            cursor = await self.db.execute(
                "SELECT 1 FROM users WHERE guild_id = ? AND user_id = ? AND currency = ?",
                (guild_id, user_id, name))
            if not await cursor.fetchone():
                amt = initial.get(name, 0)
                await self.db.execute(
                    "INSERT INTO users (guild_id, user_id, currency, balance) VALUES (?, ?, ?, ?)",
                    (guild_id, user_id, name, amt))
        await self.db.commit()

    async def get_user_ranks(self, guild_id: int, currency: str) -> dict:
        cursor = await self.db.execute(
            "SELECT user_id, balance FROM users WHERE guild_id = ? AND currency = ? ORDER BY balance DESC",
            (guild_id, currency))
        rows = await cursor.fetchall()
        infinity_ids = {row[0] for row in await (await self.db.execute("SELECT user_id FROM infinity_users")).fetchall()}
        filtered = [(r[0], r[1]) for r in rows if r[0] not in infinity_ids]
        ranks = {}
        for i, (uid, bal) in enumerate(filtered):
            ranks[uid] = {"rank": i + 1, "balance": bal}
        return ranks


db = Database()
