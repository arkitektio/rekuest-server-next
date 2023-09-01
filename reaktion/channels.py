from kante.channel import build_channel

runevent_created_broadcast, runevent_created_listen = build_channel(
    "runevent_created_broadcast"
)
