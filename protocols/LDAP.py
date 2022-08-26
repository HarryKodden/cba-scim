from __future__ import print_function

import ldap3 as ldap
import json
import logging

logger = logging.getLogger(__name__)

class LDAP(object):
  
    def __init__(self, host, username, password, base='', mode=ldap.IP_V6_PREFERRED, people_key='uid', group_key='cn', people_objectclass='inetOrgpeople', group_objectclass='groupOfMembers'):

        # Establish connection with LDAP...
        try:
            s = ldap.Server(host, get_info=ldap.ALL, mode=mode)

            self.session = ldap.Connection(s, user=username, password=password)
            if not self.session.bind():
               raise Exception("Exception during bind")

            logger.debug("LDAP Connected !")
            logger.debug(s.info)

        except Exception as e:
            logger.error("Problem connecting to LDAP {} error: {}".format(host, str(e)))

        self.base = base
        
        self.people_key = people_key
        self.group_key = group_key

        self.people_objectclass = people_objectclass
        self.group_objectclass = group_objectclass

        self.people = {}
        self.groups = {}

        self.stats = { 
            'searches' : 0,
            'reads' : 0
        }

        self.reads = 0

    def __enter__(self):
        self.get_people()
        self.get_groups()

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.session.unbind()

    def __repr__(self):
        return json.dumps(self.json(), indent=4, sort_keys=True)

    def get_stats(self):
        return self.stats

    def json(self):
        return {
            'people': self.people,
            'groups': self.groups
        }

    def search(self, base, searchScope=ldap.SUBTREE,
            searchFilter="(objectclass=*)",
            retrieveAttributes=[]):

        result = {}

        self.stats['searches'] += 1

        g = self.session.extend.standard.paged_search(
            search_base = base,
            search_filter = searchFilter,
            search_scope = searchScope,
            attributes = retrieveAttributes,
            paged_size = 5,
            generator = True
        )

        for i in g:
            self.stats['reads'] += 1
            result[i['dn']] = self.attributes(i['attributes'])

        logger.debug(result)

        return result

    @staticmethod
    def attributes(x):

        attributes = {}

        for a in x.keys():
            attributes[a] = []
            if isinstance(x[a], str):
                attributes[a] = x[a]
            else:
                for v in x[a]:
                    try:
                        if isinstance(v, bytes):
                            v = v.decode()
                    except (UnicodeDecodeError, AttributeError):
                        pass
                    attributes[a].append(v)

        return attributes

    def get_people(self):
        for _, attributes in self.search(
                self.base,
                searchFilter=f"(&(objectClass={self.people_objectclass})({self.people_key}=*))",
                retrieveAttributes=['*']
            ).items():

            if self.people_key not in attributes:
                logger.error("Missing '{}' attribute in LDAP USER Object !".format(self.people_key))
                continue

            if len(attributes[self.people_key]) > 1:
                logger.error("LDAP User key '{}' must be 1 value !".format(self.people_key))
                continue

            key = attributes[self.people_key][0]

            self.people[key] = attributes

    def get_groups(self):
        for _, attributes in self.search(
                self.base,
                searchFilter=f"(&(objectClass={self.group_objectclass})({self.group_key}=*))",
                retrieveAttributes=['*']
            ).items():

            if self.group_key not in attributes:
                logger.error("Missing '{}' attribute in LDAP GROUP Object !".format(self.group_key))
                continue

            if len(attributes[self.group_key]) > 1:
                logger.error("LDAP Group key '{}' must be 1 value !".format(self.group_key))
                continue

            key = attributes[self.group_key][0]

            members = []

            if 'member' in attributes:

                for member in attributes['member']:

                    m = member.split(',')[0].split('=')[1]

                    if m not in self.people:
                        logger.error("Member {} not in LDAP People !".format(m))
                        continue

                    members.append(m)

            attributes['member'] = members

            self.groups[key] = attributes
