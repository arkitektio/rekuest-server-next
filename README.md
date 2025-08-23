# Rekuest-Server (Next)

[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/arkitektio/rekuest-server/)
![Maintainer](https://img.shields.io/badge/maintainer-jhnnsrs-blue)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


Rekuest is one of the core services of Arkitekt. It represents a central repository of
all the connected apps and their provided functionality, their [Actions](https://arkitekt.live/docs/terminology/actions).
It also provides ways of interacting with the apps, by providing a central access point, that
apps and users can assign tasks to. Rekuest then takes care of routing the requests to the
appropriate app, which executes the task and returns the result to rekuest, which in turn routes it back
to the caller. Similar to all other Arkitekt services, Rekuest exposes a GraphQL API, that can be used to interact with it.
You can find the interactive documentation for the API [here](https://arkitekt.live/explorer).

## Core Concepts

Rekuest operates with several key abstractions:

- **Actions**: Abstract definitions of tasks or functions that can be executed. Actions define input and output parameters, but not the actual implementation.

- **Implementations**: Concrete implementations of Actions provided by connected agents. Each Implementation specifies how an Action can be executed on a specific agent.

- **Agents**: Compute nodes that can execute implementations. Agents register with Rekuest and provide implementations for various Actions.

- **Assignations**: Track the execution of a specific task. When a user requests to run an Action, an Assignation is created to manage the lifecycle of that execution.

- **Reservations**: Pre-allocate an Implementation for future use. Reservations ensure that a specific agent/implementation will be available when needed.

- **Bloks**: User interface components that can be deployed to agents for interactive workflows.

- **States**: Persistent data managed by agents, following defined schemas for structure and validation.

> [!NOTE]  
> What you are currently looking at is the next version of rekuest. It is currently under development and not ready for production. If you are looking for the current version of Rekuest, you can find it [here](https://github.com/arkitektio/rekuest-server).



## Rekuest Design

Rekuest itself is designed as a stateless service (in order to be able to scale horizontally), and
interfaces with proven open-source technologies, such as [Redis](https://redis.io/) and [RabbitMQ](https://www.rabbitmq.com/).
to route tasks to the appropriate apps. The following diagram shows the high-level design of Rekuest:

![Rekuest Design](./docs/schema.png)

## Developmental Notices

Rekuest is currently being rewritten to support other message brokers, such as [Kafka](https://kafka.apache.org/). This will
however remain an opt-in feature, and RabbitMQ will remain the default message broker. To learn more about this design decision,
please refer to the [Why Not?](https://arkitekt.live/docs/design/why-not) section.

This repository contains the next generation of Rekuest with improved architecture and expanded capabilities.
Efforts from this repository will be merged into the main Rekuest repository once the new version is ready for production.


