# --- BEGIN COPYRIGHT BLOCK ---
# Copyright (C) 2019 Red Hat, Inc.
# All rights reserved.
#
# License: GPL (version 3 or any later version).
# See LICENSE for details.
# --- END COPYRIGHT BLOCK ---

from lib389._constants import *
from lib389._mapped_object import DSLdapObject
from lib389.utils import (ds_is_older)


class Monitor(DSLdapObject):
    """An object that helps reading of cn=monitor for server statistics.
        :param instance: An instance
        :type instance: lib389.DirSrv
        :param dn: not used
    """
    def __init__(self, instance, dn=None):
        super(Monitor, self).__init__(instance=instance)
        self._dn = DN_MONITOR

    def get_connections(self):
        """Get connection related attribute values for cn=monitor

        :returns: Values of connection, currentconnections,
                  totalconnections attributes of cn=monitor
        """
        connection = self.get_attr_vals_utf8('connection')
        currentconnections = self.get_attr_vals_utf8('currentconnections')
        totalconnections = self.get_attr_vals_utf8('totalconnections')
        return (connection, currentconnections, totalconnections)

    def get_version(self):
        """Get version attribute value for cn=monitor

        :returns: Value of version attribute of cn=monitor
        """
        version = self.get_attr_vals_utf8('connection')
        return version

    def get_threads(self):
        """Get thread related attributes value for cn=monitor

        :returns: Values of threads, currentconnectionsatmaxthreads, and
                  maxthreadsperconnhits attributes of cn=monitor
        """
        threads = self.get_attr_vals_utf8('threads')
        currentconnectionsatmaxthreads = self.get_attr_vals_utf8('currentconnectionsatmaxthreads')
        maxthreadsperconnhits = self.get_attr_vals_utf8('maxthreadsperconnhits')
        return (threads, currentconnectionsatmaxthreads, maxthreadsperconnhits)

    def get_backends(self):
        """Get backends related attributes value for cn=monitor

        :returns: Values of nbackends and backendmonitordn attributes of cn=monitor
        """
        nbackends = self.get_attr_vals_utf8('nbackends')
        backendmonitordn = self.get_attr_vals_utf8('backendmonitordn')
        return (nbackends, backendmonitordn)

    def get_operations(self):
        """Get operations related attributes value for cn=monitor

        :returns: Values of opsinitiated and opscompleted attributes of cn=monitor
        """
        opsinitiated = self.get_attr_vals_utf8('opsinitiated')
        opscompleted = self.get_attr_vals_utf8('opsinitiated')
        return (opsinitiated, opscompleted)

    def get_statistics(self):
        """Get statistics attributes value for cn=monitor

        :returns: Values of dtablesize, readwaiters, entriessent,
                  bytessent, currenttime, starttime attributes of cn=monitor
        """
        dtablesize = self.get_attr_vals_utf8('dtablesize')
        readwaiters = self.get_attr_vals_utf8('readwaiters')
        entriessent = self.get_attr_vals_utf8('entriessent')
        bytessent = self.get_attr_vals_utf8('bytessent')
        currenttime = self.get_attr_vals_utf8('currenttime')
        starttime = self.get_attr_vals_utf8('starttime')
        return (dtablesize, readwaiters, entriessent, bytessent, currenttime, starttime)

    def get_status(self, use_json=False):
        return self.get_attrs_vals_utf8([
            'version',
            'threads',
            'connection',
            'currentconnections',
            'totalconnections',
            'currentconnectionsatmaxthreads',
            'maxthreadsperconnhits',
            'dtablesize',
            'readwaiters',
            'opsinitiated',
            'opscompleted',
            'entriessent',
            'bytessent',
            'currenttime',
            'starttime',
            'nbackends',
        ])


class MonitorLDBM(DSLdapObject):
    def __init__(self, instance, dn=None):
        super(MonitorLDBM, self).__init__(instance=instance)
        self._dn = DN_MONITOR_LDBM
        self._backend_keys = [
            'dbcachehits',
            'dbcachetries',
            'dbcachehitratio',
            'dbcachepagein',
            'dbcachepageout',
            'dbcacheroevict',
            'dbcacherwevict',
        ]
        if not ds_is_older("1.4.0"):
            self._backend_keys.extend([
                'normalizeddncachetries',
                'normalizeddncachehits',
                'normalizeddncachemisses',
                'normalizeddncachehitratio',
                'normalizeddncacheevictions',
                'currentnormalizeddncachesize',
                'maxnormalizeddncachesize',
                'currentnormalizeddncachecount',
                'normalizeddncachethreadsize',
                'normalizeddncachethreadslots'
            ])

    def get_status(self, use_json=False):
        return self.get_attrs_vals_utf8(self._backend_keys)


class MonitorBackend(DSLdapObject):
    """
    This is initialised from Backend in backend.py to get the right basedn.
    """

    def __init__(self, instance, dn=None):
        super(MonitorBackend, self).__init__(instance=instance, dn=dn)
        self._backend_keys = [
            'readonly',
            'entrycachehits',
            'entrycachetries',
            'entrycachehitratio',
            'currententrycachesize',
            'maxentrycachesize',
            'currententrycachecount',
            'maxentrycachecount',
            'dncachehits',
            'dncachetries',
            'dncachehitratio',
            'currentdncachesize',
            'maxdncachesize',
            'currentdncachecount',
            'maxdncachecount',
        ]
        if ds_is_older("1.4.0"):
            self._backend_keys.extend([
                'normalizeddncachetries',
                'normalizeddncachehits',
                'normalizeddncachemisses',
                'normalizeddncachehitratio',
                'currentnormalizeddncachesize',
                'maxnormalizeddncachesize',
                'currentnormalizeddncachecount'
            ])

    # Issue: get status should return a dict and the called should be
    # formatting it. See: https://pagure.io/389-ds-base/issue/50189
    def get_status(self, use_json=False):
        return self.get_attrs_vals_utf8(self._backend_keys)


class MonitorChaining(DSLdapObject):
    """
    """
    def __init__(self, instance, dn=None):
        super(MonitorChaining, self).__init__(instance=instance, dn=dn)
        self._chaining_keys = [
            'nsaddcount',
            'nsdeletecount',
            'nsmodifycount',
            'nsrenamecount',
            'nssearchbasecount',
            'nssearchonelevelcount',
            'nssearchsubtreecount',
            'nsabandoncount',
            'nsbindcount',
            'nsunbindcount',
            'nscomparecount',
            'nsopenopconnectioncount',
            'nsopenbindconnectioncount'
        ]
        self._protected = False

    def get_status(self, use_json=False):
        return self.get_attrs_vals_utf8(self._chaining_keys)


class MonitorSNMP(DSLdapObject):
    """
    """
    def __init__(self, instance, dn=None):
        super(MonitorSNMP, self).__init__(instance=instance, dn=dn)
        self._dn = DN_MONITOR_SNMP
        self._snmp_keys = [
            'anonymousbinds',
            'unauthbinds',
            'simpleauthbinds',
            'strongauthbinds',
            'bindsecurityerrors',
            'inops',
            'readops',
            'compareops',
            'addentryops',
            'removeentryops',
            'modifyentryops',
            'modifyrdnops',
            'listops',
            'searchops',
            'onelevelsearchops',
            'wholesubtreesearchops',
            'referrals',
            'chainings',
            'securityerrors',
            'errors',
            'connections',
            'connectionseq',
            'connectionsinmaxthreads',
            'connectionsmaxthreadscount',
            'bytesrecv',
            'bytessent',
            'entriesreturned',
            'referralsreturned',
            'masterentries',
            'copyentries',
            'cacheentries',
            'cachehits',
            'slavehits'
        ]

    def get_status(self, use_json=False):
        return self.get_attrs_vals_utf8(self._snmp_keys)
