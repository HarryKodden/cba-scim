# Introduction

This document explains the design to inform CBA on every update of CO-memberships for any CO that the CBA Service is connected with.

References:

- [RF 7642: System for Cross-domain Identity Management: Definitions, Overview, Concepts, and Requirements](https://www.rfc-editor.org/info/rfc7642)
- [RFC 7644: System for Cross-domain Identity Management: Protocol](https://www.rfc-editor.org/info/rfc7644)
- [SRAM](https://sram.surf.nl/landing)

## Design

CBA will be implemented as a regular SRAM Service. The CO memberschip will be reflected in the SRAM LDAP subtree for this service.

### Process updates in SBS and LDAP

Every update in SBS will be propagated into LDAP with a small delay. This delay is caused by the background process of SRAM that reads the SBS database and synchronise the contents into the LDAP once every interval period (at this moment the interval is configured as 1 minute).

### Process update to CBA.

We will create an additional background process for this service. This background process will read the SRAM LDAP and create SCIM requests that are executed towards the CBA endpoint. Also this process will be scheduled on a interval basis. At least during the first proof of concept.

The ambition is to adhere to the SCIM protocol and therefor the CBA platform will act as a SCIM server. The messages send will comply to the SCIM protocol.

As a initial setup we will create /User and /Group scim postings for all active user and group content every interval. (So no optimization during initial proof of concept)

#### Main logic

![Design](http://www.plantuml.com/plantuml/proxy?src=https://raw.githubusercontent.com/HarryKodden/cba-scim/main/assets/logic.iuml)

#### Main components

![Design](http://www.plantuml.com/plantuml/proxy?src=https://raw.githubusercontent.com/HarryKodden/cba-scim/main/assets/components.iuml)

## Proof of Concept

For the SCIM backend, the implementation is used
The synchronization logic not doing any updates if there is no difference between the LDAP attributes and the already registered details in he SCIM backend. This way we minimize the I/O foot print to just LDAP Reads and SCIM Reads most of the time.

### Example:

Inital run

```
2022-08-17 08:24:44,696 INFO SYNC started at: 2022-08-17 08:24:44.696398
2022-08-17 08:24:45,313 INFO Stats: {'reads': 15, 'writes': 12}
2022-08-17 08:24:45,313 INFO SYNC completed at: 2022-08-17 08:24:44.696398
```

Second run

```
2022-08-17 08:25:48,951 INFO SYNC started at: 2022-08-17 08:25:48.951626
2022-08-17 08:25:49,473 INFO Stats: {'reads': 27, 'writes': 0}
2022-08-17 08:25:49,473 INFO SYNC completed at: 2022-08-17 08:25:48.951626
```

## Work breakdown

- Agree on (initial) design/approach
- Agree on SCIM protocol
- Agree on scheduling mechanism Push/Pull/Polling/Notification/...
- SRAM service: Build POC
- Prepare / build API endpoints in CBA
- setup shared test environment for end to end test (solve potential firewall issues)
