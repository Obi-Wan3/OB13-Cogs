from copy import copy


class ConfigCache:
    def __init__(self):
        self.cache: dict = {}
        self.defaults: dict = {}

    def initialize(self, config: dict, defaults: dict):
        self.cache: dict = config
        self.defaults: dict = defaults

    def items(self):
        return [(guild_id, self.cache[guild_id]) for guild_id in self.cache]


class GuildCache(ConfigCache):
    def __init__(self):
        super().__init__()

    def initialize(self, config: dict, defaults: dict):
        super().initialize(config, defaults)

    def get(self, guild_id: int, key: str = None):
        cache = self.cache.get(guild_id)
        if key:
            return cache[key] if cache else self.defaults[key]
        return cache or self.defaults

    def set(self, guild_id: int, key: str, value):
        if self.cache.get(guild_id):
            self.cache[guild_id][key] = value
        else:
            self.cache[guild_id] = copy(self.defaults)
            self.cache[guild_id].update({key: value})
        return self.cache[guild_id]

    def append(self, guild_id: int, key: str, value, check: bool = False):
        if not self.cache.get(guild_id):
            self.cache[guild_id] = copy(self.defaults)
        if not check or value not in self.cache[guild_id][key]:
            self.cache[guild_id][key].append(value)

    def remove(self, guild_id: int, key: str, value, check: bool = False):
        if not self.cache.get(guild_id):
            self.cache[guild_id] = copy(self.defaults)
        if not check or value in self.cache[guild_id][key]:
            self.cache[guild_id][key].remove(value)

    def items(self):
        return super().items()


class MemberCache(ConfigCache):
    def __init__(self):
        super().__init__()

    def initialize(self, config: dict, defaults: dict):
        super().initialize(config, defaults)

    def get(self, guild_id: int, member_id: int = None, key: str = None):
        cache = self.cache.get(guild_id, {}).get(member_id)
        if member_id and key:
            return cache[key] if cache else self.defaults[key]
        elif member_id:
            return cache or self.defaults
        return self.cache.get(guild_id, {})

    def set(self, guild_id: int, member_id: int, key: str, value):
        if not self.cache.get(guild_id):
            self.cache[guild_id] = {}
        if self.cache[guild_id].get(member_id):
            self.cache[guild_id][member_id][key] = value
        else:
            self.cache[guild_id][member_id] = copy(self.defaults)
            self.cache[guild_id][member_id].update({key: value})
        return self.cache[guild_id][member_id]

    def increment(self, guild_id: int, member_id: int, key: str, value):
        if not self.cache.get(guild_id):
            self.cache[guild_id] = {}
        if not self.cache[guild_id].get(member_id):
            self.cache[guild_id][member_id] = copy(self.defaults)
        self.cache[guild_id][member_id][key] += value
        return self.cache[guild_id][member_id]

    def items(self):
        return super().items()
