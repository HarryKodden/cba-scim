#!/bin/bash

# Prepare logging

sed -i '/imklog/s/^/#/' /etc/rsyslog.conf

# Prepare CRON...

read -r -d '' CRONJOB <<- EOM
  LOG_LEVEL=${LOG_LEVEL}
  LDAP_PASSWORD='${LDAP_PASSWORD}'
  LDAP_BASENAME=${LDAP_BASENAME}
  LDAP_USERNAME=${LDAP_USERNAME}
  LDAP_HOST=${LDAP_HOST}
  LDAP_MODE=${LDAP_MODE}
  LDAP_PEOPLE_KEY=${LDAP_PEOPLE_KEY}
  LDAP_PEOPLE_OBJECTCLASS=${LDAP_PEOPLE_OBJECTCLASS}
  LDAP_GROUP_KEY=${LDAP_GROUP_KEY}
  LDAP_GROUP_OBJECTCLASS=${LDAP_GROUP_OBJECTCLASS}
  SCIM_SERVER=${SCIM_SERVER}
  SCIM_BEARER='${SCIM_BEARER}'
  SCIM_VERIFY=${SCIM_VERIFY}
  python3 /root/sync >> /var/log/sync.log 2>&1
EOM
crontab -l | { cat; echo "* * * * * "$CRONJOB; } | crontab -

# Start services...
rsyslogd 
service cron start

# Runtime...
sleep infinity