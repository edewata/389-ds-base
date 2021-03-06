# --- BEGIN COPYRIGHT BLOCK ---
# Copyright (C) 2015 Red Hat, Inc.
# All rights reserved.
#
# License: GPL (version 3 or any later version).
# See LICENSE for details.
# --- END COPYRIGHT BLOCK ---

import os
import ldap

from lib389._constants import *
from lib389.properties import *
from lib389 import DirSrv, Entry, InvalidArgumentError

from lib389._mapped_object import DSLdapObject
from lib389.utils import ds_is_older


class Changelog5(DSLdapObject):
    """Represents the Directory Server changelog. This is used for
    replication. Only one changelog is needed for every server.

    :param instance: An instance
    :type instance: lib389.DirSrv
    """

    def __init__(self, instance, dn='cn=changelog5,cn=config'):
        super(Changelog5, self).__init__(instance, dn)
        self._rdn_attribute = 'cn'
        self._must_attributes = ['cn', 'nsslapd-changelogdir']
        self._create_objectclasses = [
            'top',
            'nsChangelogConfig',
        ]
        if ds_is_older('1.4.0'):
            self._create_objectclasses = [
                'top',
                'extensibleobject',
            ]
        self._protected = False

    def set_max_entries(self, value):
        """Configure the max entries the changelog can hold.

        :param value: the number of entries.
        :type value: str
        """
        self.replace('nsslapd-changelogmaxentries', value)

    def set_trim_interval(self, value):
        """The time between changelog trims in seconds.

        :param value: The time in seconds
        :type value: str
        """
        self.replace('nsslapd-changelogtrim-interval', value)

    def set_max_age(self, value):
        """The maximum age of entries in the changelog.

        :param value: The age with a time modifier of s, m, h, d, w.
        :type value: str
        """
        self.replace('nsslapd-changelogmaxage', value)


class ChangelogLegacy(object):
    """An object that helps to work with changelog entry

    :param conn: An instance
    :type conn: lib389.DirSrv
    """

    proxied_methods = 'search_s getEntry'.split()

    def __init__(self, conn):
        self.conn = conn
        self.log = conn.log

    def __getattr__(self, name):
        if name in Changelog.proxied_methods:
            return DirSrv.__getattr__(self.conn, name)

    def list(self, suffix=None, changelogdn=DN_CHANGELOG):
        """Get a changelog entry using changelogdn parameter

        :param suffix: Not used
        :type suffix: str
        :param changelogdn: DN of the changelog entry, DN_CHANGELOG by default
        :type changelogdn: str

        :returns: Search result of the replica agreements.
                  Enpty list if nothing was found
        """

        base = changelogdn
        filtr = "(objectclass=extensibleobject)"

        # now do the effective search
        try:
            ents = self.conn.search_s(base, ldap.SCOPE_BASE, filtr)
        except ldap.NO_SUCH_OBJECT:
            # There are no objects to select from, se we return an empty array
            # as we do in DSLdapObjects
            ents = []
        return ents

    def create(self, dbname=DEFAULT_CHANGELOG_DB):
        """Add and return the replication changelog entry.

        :param dbname: Database name, it will be used for creating
                       a changelog dir path
        :type dbname: str
        """

        dn = DN_CHANGELOG
        attribute, changelog_name = dn.split(",")[0].split("=", 1)
        dirpath = os.path.join(os.path.dirname(self.conn.dbdir), dbname)
        entry = Entry(dn)
        entry.update({
            'objectclass': ("top", "extensibleobject"),
            CHANGELOG_PROPNAME_TO_ATTRNAME[CHANGELOG_NAME]: changelog_name,
            CHANGELOG_PROPNAME_TO_ATTRNAME[CHANGELOG_DIR]: dirpath
        })
        self.log.debug("adding changelog entry: %r", entry)
        self.conn.changelogdir = dirpath
        try:
            self.conn.add_s(entry)
        except ldap.ALREADY_EXISTS:
            self.log.warning("entry %s already exists", dn)
        return dn

    def delete(self):
        """Delete the changelog entry

        :raises: LDAPError - failed to delete changelog entry
        """

        try:
            self.conn.delete_s(DN_CHANGELOG)
        except ldap.LDAPError as e:
            self.log.error('Failed to delete the changelog: %s', e)
            raise

    def setProperties(self, changelogdn=None, properties=None):
        """Set the properties of the changelog entry.

        :param changelogdn: DN of the changelog
        :type changelogdn: str
        :param properties: Dictionary of properties
        :type properties: dict

        :returns: None
        :raises: - ValueError - if invalid properties
                 - ValueError - if changelog entry is not found
                 - InvalidArgumentError - changelog DN is missing

        :supported properties are:
                CHANGELOG_NAME, CHANGELOG_DIR, CHANGELOG_MAXAGE,
                CHANGELOG_MAXENTRIES, CHANGELOG_TRIM_INTERVAL,
                CHANGELOG_COMPACT_INTV, CHANGELOG_CONCURRENT_WRITES,
                CHANGELOG_ENCRYPT_ALG, CHANGELOG_SYM_KEY
        """

        if not changelogdn:
            raise InvalidArgumentError("changelog DN is missing")

        ents = self.conn.changelog.list(changelogdn=changelogdn)
        if len(ents) != 1:
            raise ValueError("Changelog entry not found: %s" % changelogdn)

        # check that the given properties are valid
        for prop in properties:
            # skip the prefix to add/del value
            if not inProperties(prop, CHANGELOG_PROPNAME_TO_ATTRNAME):
                raise ValueError("unknown property: %s" % prop)

        # build the MODS
        mods = []
        for prop in properties:
            # take the operation type from the property name
            val = rawProperty(prop)
            if str(prop).startswith('+'):
                op = ldap.MOD_ADD
            elif str(prop).startswith('-'):
                op = ldap.MOD_DELETE
            else:
                op = ldap.MOD_REPLACE

            mods.append((op, CHANGELOG_PROPNAME_TO_ATTRNAME[val],
                         properties[prop]))

        # that is fine now to apply the MOD
        self.conn.modify_s(ents[0].dn, mods)

    def getProperties(self, changelogdn=None, properties=None):
        """Get a dictionary of the requested properties.
        If properties parameter is missing, it returns all the properties.

        NotImplemented
        """

        raise NotImplemented
