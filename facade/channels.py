from kante.channel import build_channel

node_created_broadcast, node_created_listen = build_channel("node_created_broadcast")

agent_updated_broadcast, agent_updated_listen = build_channel("agent_updated_broadcast")

assignation_broadcast, assignation_listen = build_channel("assignation_broadcast")

reservation_broadcast, reservation_listen = build_channel("reservation_broadcast")

assignation_event_broadcast, assignation_event_listen = build_channel("assignation_event_broadcast")

provision_event_broadcast, provision_event_listen = build_channel("provision_event_broadcast")

reservation_event_broadcast, reservation_event_listen = build_channel("reservation_event_broadcast")