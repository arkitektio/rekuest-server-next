from kante.channel import build_channel

node_created_broadcast, node_created_listen = build_channel("node_created_broadcast")

agent_updated_broadcast, agent_updated_listen = build_channel("agent_updated_broadcast")