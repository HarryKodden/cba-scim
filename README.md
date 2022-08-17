# Introduction

This document explains the design to inform CBA on every update of CO-memberships for any CO that the CBA Service is connected with.

## Design

CBA will be implemented as a regular SRAM Service. The CO memberschip will be reflected in the SRAM LDAP subtree for this service.

### Process updates in SBS and LDAP

Every update in SBS will be propagated into LDAP with a small delay. This delay is caused by the background process of SRAM that reads the SBS database and synchronise the contents into the LDAP once every interval period (at this moment the interval is configured as 1 minute).

### Process update to CBA.

We will create an additional background process for this service. This background process will read the SRAM LDAP and create SCIM requests that are executed towards the CBA endpoint. Also this process will be scheduled on a interval basis. At least during the first proof of concept.

The ambition is to adhere to the SCIM protocol and therefor the CBA platform will act as a SCIM server. The messages send will comply to the SCIM protocol.

As a initial setup we will create /User and /Group scim postings for all active user and group content every interval. (So no optimization during initial proof of concept)

#### UML: Cronjob CBA Updater

![Design](http://www.plantuml.com/plantuml/proxy?src=https://raw.githubusercontent.com/HarryKodden/cba-scim/main/assets/design.iuml)

## Work breakdown

- Agree on (initial) design/approach
- Agree on SCIM protocol
- Agree on scheduling mechanism Push/Pull/Polling/Notification/...
- SRAM service: Build POC
- Prepare / build API endpoints in CBA
- setup shared test environment for end to end test (solve potential firewall issues)
