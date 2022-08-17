#!/usr/bin/env python
from __future__ import print_function

import os
import logging

from LDAP import LDAP
from SCIM import SCIM

from datetime import datetime

# Setup logging
log_level = os.environ.get('LOG_LEVEL', 'INFO')

logging.basicConfig(
    level=logging.getLevelName(log_level),
    format='%(asctime)s %(levelname)s %(message)s')

logger = logging.getLogger('root')


def sync():
    start_time = datetime.now()
    logger.info("SYNC started at: {}".format(start_time))

    with SCIM(os.environ.get(
            'SCIM_SERVER', 'http://localhost'),
            os.environ.get('SCIM_BEARER', None),
            verify=(os.environ.get('SCIM_VERIFY', "True").upper() == 'TRUE')
        ) as my_scim:

        logger.debug(my_scim)

        with LDAP(
                os.environ['LDAP_HOST'],

                os.environ['LDAP_USERNAME'],
                os.environ['LDAP_PASSWORD'],
                
                base = os.environ['LDAP_BASENAME'],
                mode = os.environ['LDAP_MODE'],

                people_key = os.environ['LDAP_PEOPLE_KEY'],
                people_objectclass = os.environ['LDAP_PEOPLE_OBJECTCLASS'],

                group_key = os.environ['LDAP_GROUP_KEY'],
                group_objectclass = os.environ['LDAP_GROUP_OBJECTCLASS']
                
            ) as my_ldap:

            logger.debug(my_ldap)
        
            for name in my_scim.users.keys():
                if name not in my_ldap.people:
                    my_scim.del_user(name)

            for name in my_scim.groups.keys():
                if name not in my_ldap.groups:
                    my_scim.del_group(name)

            for name, attributes in my_ldap.people.items():

                my_scim.add_user(
                    name,
                    externalId = attributes.get('eduPersonUniqueId',''),
                    displayName = attributes.get('displayName',''), 
                    givenName = attributes.get('givenName',[])[0],
                    familyName = attributes.get('sn', [])[0],
                    mail = attributes.get('mail',[]),
                    certificates = attributes.get('sshPublicKey', [])
                )

            for name, attributes in my_ldap.groups.items():
                my_scim.add_group(name, [ my_scim.users[u]['id'] for u in attributes.get('member',[]) ])
                
        logger.info(f"Stats: {my_scim.stats}")


    logger.info("SYNC completed at: {}".format(start_time))

if __name__ == "__main__":
    sync()
