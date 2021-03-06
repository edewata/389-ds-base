# --- BEGIN COPYRIGHT BLOCK ---
# Copyright (C) 2018 Red Hat, Inc.
# All rights reserved.
#
# License: GPL (version 3 or any later version).
# See LICENSE for details.
# --- END COPYRIGHT BLOCK ---

import json
import ldap
from getpass import getpass
from lib389._constants import *
from lib389.changelog import Changelog5
from lib389.utils import is_a_dn
from lib389.replica import Replicas, BootstrapReplicationManager
from lib389.tasks import CleanAllRUVTask, AbortCleanAllRUVTask
from lib389._mapped_object import DSLdapObjects

arg_to_attr = {
        # replica config
        'replica_id': 'nsds5replicaid',
        'repl_purge_delay': 'nsds5replicapurgedelay',
        'repl_tombstone_purge_interval': 'nsds5replicatombstonepurgeinterval',
        'repl_fast_tombstone_purging': 'nsds5ReplicaPreciseTombstonePurging',
        'repl_bind_group': 'nsds5replicabinddngroup',
        'repl_bind_group_interval': 'nsds5replicabinddngroupcheckinterval',
        'repl_protocol_timeout': 'nsds5replicaprotocoltimeout',
        'repl_backoff_min': 'nsds5replicabackoffmin',
        'repl_backoff_max': 'nsds5replicabackoffmax',
        'repl_release_timeout': 'nsds5replicareleasetimeout',
        # Changelog
        'cl_dir': 'nsslapd-changelogdir',
        'max_entries': 'nsslapd-changelogmaxentries',
        'max_age': 'nsslapd-changelogmaxage',
        'compact_interval': 'nsslapd-changelogcompactdb-interval',
        'trim_interval': 'nsslapd-changelogtrim-interval',
        'encrypt_algo': 'nsslapd-encryptionalgorithm',
        'encrypt_key': 'nssymmetrickey',
        # Agreement
        'host': 'nsds5replicahost',
        'port': 'nsds5replicaport',
        'conn_protocol': 'nsds5replicatransportinfo',
        'bind_dn': 'nsds5replicabinddn',
        'bind_passwd': 'nsds5replicacredentials',
        'bind_method': 'nsds5replicabindmethod',
        'frac_list': 'nsds5replicatedattributelist',
        'frac_list_total': 'nsds5replicatedattributelisttotal',
        'strip_list': 'nsds5replicastripattrs',
        'schedule': 'nsds5replicaupdateschedule',
        'conn_timeout': 'nsds5replicatimeout',
        'protocol_timeout': 'nsds5replicaprotocoltimeout',
        'wait_async_results': 'nsds5replicawaitforasyncresults',
        'busy_wait_time': 'nsds5replicabusywaittime',
        'session_pause_time': 'nsds5replicaSessionPauseTime',
        'flow_control_window': 'nsds5replicaflowcontrolwindow',
        'flow_control_pause': 'nsds5replicaflowcontrolpause',
        # Additional Winsync Agmt attrs
        'win_subtree': 'nsds7windowsreplicasubtree',
        'ds_subtree': 'nsds7directoryreplicasubtree',
        'sync_users': 'nsds7newwinusersyncenabled',
        'sync_groups': 'nsds7newwingroupsyncenabled',
        'win_domain': 'nsds7windowsDomain',
        'sync_interval': 'winsyncinterval',
        'one_way_sync': 'onewaysync',
        'move_action': 'winsyncmoveAction',
        'ds_filter': 'winsyncdirectoryfilter',
        'win_filter': 'winsyncwindowsfilter',
        'subtree_pair': 'winSyncSubtreePair'
    }


def get_agmt(inst, args, winsync=False):
    agmt_name = get_agmt_name(args)
    replicas = Replicas(inst)
    replica = replicas.get(args.suffix)
    agmts = replica.get_agreements(winsync=winsync)
    try:
        agmt = agmts.get(agmt_name)
    except ldap.NO_SUCH_OBJECT:
        raise ValueError("Could not find the agreement \"{}\" for suffix \"{}\"".format(agmt_name, args.suffix))
    return agmt


def get_agmt_name(args):
    agmt_name = args.AGMT_NAME[0]
    if agmt_name.startswith('"') and agmt_name.endswith('"'):
        # Remove quotes from quoted value
        agmt_name = agmt_name[1:-1]
    return agmt_name


def _args_to_attrs(args):
    attrs = {}
    for arg in vars(args):
        val = getattr(args, arg)
        if arg in arg_to_attr and val is not None:
            attrs[arg_to_attr[arg]] = val
    return attrs


#
# Replica config
#
def enable_replication(inst, basedn, log, args):
    repl_root = args.suffix
    role = args.role.lower()
    rid = args.replica_id

    if role == "master":
        repl_type = '3'
        repl_flag = '1'
    elif role == "hub":
        repl_type = '2'
        repl_flag = '1'
    elif role == "consumer":
        repl_type = '2'
        repl_flag = '0'
    else:
        # error - unknown type
        raise ValueError("Unknown replication role ({}), you must use \"master\", \"hub\", or \"consumer\"".format(role))

    # Start the propeties and update them as needed
    repl_properties = {
        'cn': 'replica',
        'nsDS5ReplicaRoot': repl_root,
        'nsDS5Flags': repl_flag,
        'nsDS5ReplicaType': repl_type,
        'nsDS5ReplicaId': '65535'
        }

    # Validate master settings
    if role == "master":
        # Do we have a rid?
        if not args.replica_id or args.replica_id is None:
            # Error, master needs a rid TODO
            raise ValueError('You must specify the replica ID (--replica-id) when enabling a \"master\" replica')

        # is it a number?
        try:
            rid_num = int(rid)
        except ValueError:
            raise ValueError("--replica-id expects a number between 1 and 65534")

        # Is it in range?
        if rid_num < 1 or rid_num > 65534:
            raise ValueError("--replica-id expects a number between 1 and 65534")

        # rid is good add it to the props
        repl_properties['nsDS5ReplicaId'] = args.replica_id

    # Bind DN or Bind DN Group?
    if args.bind_group_dn:
        repl_properties['nsDS5ReplicaBindDNGroup'] = args.bind_group_dn
    if args.bind_dn:
        repl_properties['nsDS5ReplicaBindDN'] = args.bind_dn

    # First create the changelog
    cl = Changelog5(inst)
    try:
        cl.create(properties={
            'cn': 'changelog5',
            'nsslapd-changelogdir': inst.get_changelog_dir()
        })
    except ldap.ALREADY_EXISTS:
        pass

    # Finally enable replication
    replicas = Replicas(inst)
    try:
        replicas.create(properties=repl_properties)
    except ldap.ALREADY_EXISTS:
        raise ValueError("Replication is already enabled for this suffix")

    # Create replication manager if password was provided
    if args.bind_dn and args.bind_passwd:
        cn_rdn = args.bind_dn.split(",", 1)[0]
        cn_val = cn_rdn.split("=", 1)[1]
        manager = BootstrapReplicationManager(inst, dn=args.bind_dn)
        try:
            manager.create(properties={
                'cn': cn_val,
                'userPassword': args.bind_passwd
            })
        except ldap.ALREADY_EXISTS:
            # Already there, but could have different password.  Delete and recreate
            manager.delete()
            manager.create(properties={
                'cn': cn_val,
                'userPassword': args.bind_passwd
            })
        except ldap.NO_SUCH_OBJECT:
            # Invalid Entry
            raise ValueError("Failed to add replication manager because the base DN of the entry does not exist")
        except ldap.LDAPError as e:
            # Some other bad error
            raise ValueError("Failed to create replication manager entry: " + str(e))

    log.info("Replication successfully enabled for \"{}\"".format(repl_root))


def disable_replication(inst, basedn, log, args):
    replicas = Replicas(inst)
    try:
        replica = replicas.get(args.suffix)
        replica.delete()
    except ldap.NO_SUCH_OBJECT:
        raise ValueError("Backend \"{}\" is not enabled for replication".format(args.suffix))
    log.info("Replication disabled for \"{}\"".format(args.suffix))


def promote_replica(inst, basedn, log, args):
    replicas = Replicas(inst)
    replica = replicas.get(args.suffix)
    role = args.newrole.lower()

    if role == 'master':
        newrole = ReplicaRole.MASTER
        if args.replica_id is None:
            raise ValueError("You need to provide a replica ID (--replica-id) to promote replica to a master")
    elif role == 'hub':
        newrole = ReplicaRole.HUB
    else:
        raise ValueError("Invalid role ({}), you must use either \"master\" or \"hub\"".format(role))

    replica.promote(newrole, binddn=args.bind_dn, binddn_group=args.bind_group_dn, rid=args.replica_id)
    log.info("Successfully promoted replica to \"{}\"".format(role))


def demote_replica(inst, basedn, log, args):
    replicas = Replicas(inst)
    replica = replicas.get(args.suffix)
    role = args.newrole.lower()

    if role == 'hub':
        newrole = ReplicaRole.HUB
    elif role == 'consumer':
        newrole = ReplicaRole.CONSUMER
    else:
        raise ValueError("Invalid role ({}), you must use either \"hub\" or \"consumer\"".format(role))

    replica.demote(newrole)
    log.info("Successfully demoted replica to \"{}\"".format(role))


def list_suffixes(inst, basedn, log, args):
    suffixes = []
    replicas = Replicas(inst).list()
    for replica in replicas:
        suffixes.append(replica.get_suffix())

    if args.json:
        log.info(json.dumps({"type": "list", "items": suffixes}))
    else:
        if len(suffixes) == 0:
            log.info("There are no replicated suffixes")
        else:
            for suffix in suffixes:
                log.info(suffix)


def get_repl_status(inst, basedn, log, args):
    replicas = Replicas(inst)
    replica = replicas.get(args.suffix)
    status = replica.status(binddn=args.bind_dn, bindpw=args.bind_passwd)
    if args.json:
        log.info(json.dumps({"type": "list", "items": status}))
    else:
        for agmt in status:
            log.info(agmt)


def get_repl_winsync_status(inst, basedn, log, args):
    replicas = Replicas(inst)
    replica = replicas.get(args.suffix)
    status = replica.status(binddn=args.bind_dn, bindpw=args.bind_passwd, winsync=True)
    if args.json:
        log.info(json.dumps({"type": "list", "items": status}))
    else:
        for agmt in status:
            log.info(agmt)


def get_repl_config(inst, basedn, log, args):
    replicas = Replicas(inst)
    replica = replicas.get(args.suffix)
    if args and args.json:
        log.info(replica.get_all_attrs_json())
    else:
        log.info(replica.display())


def set_repl_config(inst, basedn, log, args):
    replicas = Replicas(inst)
    replica = replicas.get(args.suffix)
    attrs = _args_to_attrs(args)
    did_something = False

    # Add supplier DNs
    if args.repl_add_bind_dn is not None:
        if not is_a_dn(args.repl_add_bind_dn):
            raise ValueError("The replica bind DN is not a valid DN")
        replica.add('nsds5ReplicaBindDN', args.repl_add_bind_dn)
        did_something = True

    # Remove supplier DNs
    if args.repl_del_bind_dn is not None:
        replica.remove('nsds5ReplicaBindDN', args.repl_del_bind_dn)
        did_something = True

    # Add referral
    if args.repl_add_ref is not None:
        replica.add('nsDS5ReplicaReferral', args.repl_add_ref)
        did_something = True

    # Remove referral
    if args.repl_del_ref is not None:
        replica.remove('nsDS5ReplicaReferral', args.repl_del_ref)
        did_something = True

    # Handle the rest of the changes that use mod_replace
    replace_list = []

    for attr, value in attrs.items():
        if value == "":
            # Delete value
            replica.remove_all(attr)
            did_something = True
        else:
            replace_list.append((attr, value))
    if len(replace_list) > 0:
        replica.replace_many(*replace_list)
    elif not did_something:
        raise ValueError("There are no changes to set in the replica")

    log.info("Successfully updated replication configuration")


def create_cl(inst, basedn, log, args):
    cl = Changelog5(inst)
    try:
        cl.create(properties={
            'cn': 'changelog5',
            'nsslapd-changelogdir': inst.get_changelog_dir()
        })
    except ldap.ALREADY_EXISTS:
        raise ValueError("Changelog already exists")
    log.info("Successfully created replication changelog")


def delete_cl(inst, basedn, log, args):
    cl = Changelog5(inst)
    try:
        cl.delete()
    except ldap.NO_SUCH_OBJECT:
        raise ValueError("There is no changelog to delete")
    log.info("Successfully deleted replication changelog")


def set_cl(inst, basedn, log, args):
    cl = Changelog5(inst)
    attrs = _args_to_attrs(args)
    replace_list = []
    did_something = False
    for attr, value in attrs.items():
        if value == "":
            cl.remove_all(attr)
            did_something = True
        else:
            replace_list.append((attr, value))
    if len(replace_list) > 0:
        cl.replace_many(*replace_list)
    elif not did_something:
        raise ValueError("There are no changes to set for the replication changelog")

    log.info("Successfully updated replication changelog")


def get_cl(inst, basedn, log, args):
    cl = Changelog5(inst)
    if args and args.json:
        log.info(cl.get_all_attrs_json())
    else:
        log.info(cl.display())


def create_repl_manager(inst, basedn, log, args):
    manager_cn = "replication manager"
    repl_manager_password = ""
    repl_manager_password_confirm = ""

    if args.name:
        manager_cn = args.name

    if is_a_dn(manager_cn):
        # A full DN was provided, make sure it uses "cn" for the RDN
        if manager_cn.split("=", 1)[0].lower() != "cn":
            raise ValueError("Replication manager DN must use \"cn\" for the rdn attribute")
        manager_dn = manager_cn
        manager_rdn = manager_dn.split(",", 1)[0]
        manager_cn = manager_rdn.split("=", 1)[1]
    else:
        manager_dn = "cn={},cn=config".format(manager_cn)

    if args.passwd:
        repl_manager_password = args.passwd
    else:
        # Prompt for password
        while 1:
            while repl_manager_password == "":
                repl_manager_password = getpass("Enter replication manager password: ")
            while repl_manager_password_confirm == "":
                repl_manager_password_confirm = getpass("Confirm replication manager password: ")
            if repl_manager_password_confirm == repl_manager_password:
                break
            else:
                log.info("Passwords do not match!\n")
                repl_manager_password = ""
                repl_manager_password_confirm = ""

    manager = BootstrapReplicationManager(inst, dn=manager_dn)
    try:
        manager.create(properties={
            'cn': manager_cn,
            'userPassword': repl_manager_password
        })
        if args.suffix:
            # Add supplier DN to config only if add succeeds
            replicas = Replicas(inst)
            replica = replicas.get(args.suffix)
            try:
                replica.add('nsds5ReplicaBindDN', manager_dn)
            except ldap.TYPE_OR_VALUE_EXISTS:
                pass
        log.info("Successfully created replication manager: " + manager_dn)
    except ldap.ALREADY_EXISTS:
        log.info("Replication Manager ({}) already exists, recreating it...".format(manager_dn))
        # Already there, but could have different password.  Delete and recreate
        manager.delete()
        manager.create(properties={
            'cn': manager_cn,
            'userPassword': repl_manager_password
        })
        if args.suffix:
            # Add supplier DN to config only if add succeeds
            replicas = Replicas(inst)
            replica = replicas.get(args.suffix)
            try:
                replica.add('nsds5ReplicaBindDN', manager_dn)
            except ldap.TYPE_OR_VALUE_EXISTS:
                pass

        log.info("Successfully created replication manager: " + manager_dn)


def del_repl_manager(inst, basedn, log, args):
    if is_a_dn(args.name):
        manager_dn = args.name
    else:
        manager_dn = "cn={},cn=config".format(args.name)
    manager = BootstrapReplicationManager(inst, dn=manager_dn)
    manager.delete()
    if args.suffix:
        # Add supplier DN to config
        replicas = Replicas(inst)
        replica = replicas.get(args.suffix)
        replica.remove('nsds5ReplicaBindDN', manager_dn)
    log.info("Successfully deleted replication manager: " + manager_dn)


#
# Agreements
#
def list_agmts(inst, basedn, log, args):
    # List regular DS agreements
    replicas = Replicas(inst)
    replica = replicas.get(args.suffix)
    agmts = replica.get_agreements().list()

    result = {"type": "list", "items": []}
    for agmt in agmts:
        if args.json:
            entry = agmt.get_all_attrs_json()
            # Append decoded json object, because we are going to dump it later
            result['items'].append(json.loads(entry))
        else:
            log.info(agmt.display())
    if args.json:
        log.info(json.dumps(result))


def add_agmt(inst, basedn, log, args):
    repl_root = args.suffix
    bind_method = args.bind_method.lower()
    replicas = Replicas(inst)
    replica = replicas.get(args.suffix)
    agmts = replica.get_agreements()

    # Process fractional settings
    frac_list = None
    if args.frac_list:
        frac_list = "(objectclass=*) $ EXCLUDE"
        for attr in args.frac_list.split():
            frac_list += " " + attr

    frac_total_list = None
    if args.frac_list_total:
        frac_total_list = "(objectclass=*) $ EXCLUDE"
        for attr in args.frac_list_total.split():
            frac_total_list += " " + attr

    # Required properties
    properties = {
            'cn': get_agmt_name(args),
            'nsDS5ReplicaRoot': repl_root,
            'description': get_agmt_name(args),
            'nsDS5ReplicaHost': args.host,
            'nsDS5ReplicaPort': args.port,
            'nsDS5ReplicaBindMethod': bind_method,
            'nsDS5ReplicaTransportInfo': args.conn_protocol
        }

    # Add optional properties
    if args.bind_dn is not None:
        if not is_a_dn(args.bind_dn):
            raise ValueError("The replica bind DN is not a valid DN")
        properties['nsDS5ReplicaBindDN'] = args.bind_dn
    if args.bind_passwd is not None:
        properties['nsDS5ReplicaCredentials'] = args.bind_passwd
    if args.schedule is not None:
        properties['nsds5replicaupdateschedule'] = args.schedule
    if frac_list is not None:
        properties['nsds5replicatedattributelist'] = frac_list
    if frac_total_list is not None:
        properties['nsds5replicatedattributelisttotal'] = frac_total_list
    if args.strip_list is not None:
        properties['nsds5replicastripattrs'] = args.strip_list

    # We do need the bind dn and credentials for none-sasl bind methods
    if (bind_method == 'simple' or 'sslclientauth') and (args.bind_dn is None or args.bind_passwd is None):
        raise ValueError("You need to set the bind dn (--bind-dn) and the password (--bind-passwd) for bind method ({})".format(bind_method))

    # Create the agmt
    try:
        agmts.create(properties=properties)
    except ldap.ALREADY_EXISTS:
        raise ValueError("A replication agreement with the same name already exists")

    log.info("Successfully created replication agreement \"{}\"".format(get_agmt_name(args)))
    if args.init:
        init_agmt(inst, basedn, log, args)


def delete_agmt(inst, basedn, log, args):
    agmt = get_agmt(inst, args)
    agmt.delete()
    log.info("Agreement has been successfully deleted")


def enable_agmt(inst, basedn, log, args):
    agmt = get_agmt(inst, args)
    agmt.resume()
    log.info("Agreement has been enabled")


def disable_agmt(inst, basedn, log, args):
    agmt = get_agmt(inst, args)
    agmt.pause()
    log.info("Agreement has been disabled")


def init_agmt(inst, basedn, log, args):
    agmt = get_agmt(inst, args)
    agmt.begin_reinit()
    log.info("Agreement initialization started...")


def check_init_agmt(inst, basedn, log, args):
    agmt = get_agmt(inst, args)
    (done, inprogress, error) = agmt.check_reinit()
    status = "Unknown"
    if done:
        status = "Agreement successfully initialized."
    elif inprogress:
        status = "Agreement initialization in progress."
    elif error:
        status = "Agreement initialization failed."
    if args.json:
        log.info(json.dumps(status))
    else:
        log.info(status)


def set_agmt(inst, basedn, log, args):
    agmt = get_agmt(inst, args)
    attrs = _args_to_attrs(args)
    modlist = []
    did_something = False
    for attr, value in attrs.items():
        if value == "":
            # Delete value
            agmt.remove_all(attr)
            did_something = True
        else:
            if attr == 'nsds5replicatedattributelist' or attr == 'nsds5replicatedattributelisttotal':
                frac_list = "(objectclass=*) $ EXCLUDE"
                for frac_attr in value.split():
                    frac_list += " " + frac_attr
                value = frac_list
            modlist.append((attr, value))

    if len(modlist) > 0:
        agmt.replace_many(*modlist)
    elif not did_something:
        raise ValueError("There are no changes to set in the agreement")

    log.info("Successfully updated agreement")


def get_repl_agmt(inst, basedn, log, args):
    agmt = get_agmt(inst, args)
    if args.json:
        log.info(agmt.get_all_attrs_json())
    else:
        log.info(agmt.display())


def poke_agmt(inst, basedn, log, args):
    # Send updates now
    agmt = get_agmt(inst, args)
    agmt.pause()
    agmt.resume()
    log.info("Agreement has been poked")


def get_agmt_status(inst, basedn, log, args):
    agmt = get_agmt(inst, args)
    if args.bind_dn is not None and args.bind_passwd is None:
        args.bind_passwd = ""
        while args.bind_passwd == "":
            args.bind_passwd = getpass("Enter password for \"{}\": ".format(args.bind_dn))
    status = agmt.status(use_json=args.json, binddn=args.bind_dn, bindpw=args.bind_passwd)
    log.info(status)


#
# Winsync agreement specfic functions
#
def list_winsync_agmts(inst, basedn, log, args):
    # List regular DS agreements
    replicas = Replicas(inst)
    replica = replicas.get(args.suffix)
    agmts = replica.get_agreements(winsync=True).list()

    result = {"type": "list", "items": []}
    for agmt in agmts:
        if args.json:
            entry = agmt.get_all_attrs_json()
            # Append decoded json object, because we are going to dump it later
            result['items'].append(json.loads(entry))
        else:
            log.info(agmt.display())
    if args.json:
        log.info(json.dumps(result))


def add_winsync_agmt(inst, basedn, log, args):
    replicas = Replicas(inst)
    replica = replicas.get(args.suffix)
    agmts = replica.get_agreements(winsync=True)

    # Process fractional settings
    frac_list = None
    if args.frac_list:
        frac_list = "(objectclass=*) $ EXCLUDE"
        for attr in args.frac_list.split():
            frac_list += " " + attr

    if not is_a_dn(args.bind_dn):
        raise ValueError("The replica bind DN is not a valid DN")

    # Required properties
    properties = {
            'cn': get_agmt_name(args),
            'nsDS5ReplicaRoot': args.suffix,
            'description': get_agmt_name(args),
            'nsDS5ReplicaHost': args.host,
            'nsDS5ReplicaPort': args.port,
            'nsDS5ReplicaTransportInfo': args.conn_protocol,
            'nsDS5ReplicaBindDN': args.bind_dn,
            'nsDS5ReplicaCredentials': args.bind_passwd,
            'nsds7windowsreplicasubtree': args.win_subtree,
            'nsds7directoryreplicasubtree': args.ds_subtree,
            'nsds7windowsDomain': args.win_domain,
        }

    # Add optional properties
    if args.sync_users is not None:
        properties['nsds7newwinusersyncenabled'] = args.sync_users
    if args.sync_groups is not None:
        properties['nsds7newwingroupsyncenabled'] = args.sync_groups
    if args.sync_interval is not None:
        properties['winsyncinterval'] = args.sync_interval
    if args.one_way_sync is not None:
        properties['onewaysync'] = args.one_way_sync
    if args.move_action is not None:
        properties['winsyncmoveAction'] = args.move_action
    if args.ds_filter is not None:
        properties['winsyncdirectoryfilter'] = args.ds_filter
    if args.win_filter is not None:
        properties['winsyncwindowsfilter'] = args.win_filter
    if args.schedule is not None:
        properties['nsds5replicaupdateschedule'] = args.schedule
    if frac_list is not None:
        properties['nsds5replicatedattributelist'] = frac_list

    # Create the agmt
    try:
        agmts.create(properties=properties)
    except ldap.ALREADY_EXISTS:
        raise ValueError("A replication agreement with the same name already exists")

    log.info("Successfully created winsync replication agreement \"{}\"".format(get_agmt_name(args)))
    if args.init:
        init_winsync_agmt(inst, basedn, log, args)


def delete_winsync_agmt(inst, basedn, log, args):
    agmt = get_agmt(inst, args, winsync=True)
    agmt.delete()
    log.info("Agreement has been successfully deleted")


def set_winsync_agmt(inst, basedn, log, args):
    agmt = get_agmt(inst, args, winsync=True)

    attrs = _args_to_attrs(args)
    modlist = []
    did_something = False
    for attr, value in list(attrs.items()):
        if value == "":
            # Delete value
            agmt.remove_all(attr)
            did_something = True
        else:
            modlist.append((attr, value))
    if len(modlist) > 0:
        agmt.replace_many(*modlist)
    elif not did_something:
        raise ValueError("There are no changes to set in the agreement")

    log.info("Successfully updated agreement")


def enable_winsync_agmt(inst, basedn, log, args):
    agmt = get_agmt(inst, args, winsync=True)
    agmt.resume()
    log.info("Agreement has been enabled")


def disable_winsync_agmt(inst, basedn, log, args):
    agmt = get_agmt(inst, args, winsync=True)
    agmt.pause()
    log.info("Agreement has been disabled")


def init_winsync_agmt(inst, basedn, log, args):
    agmt = get_agmt(inst, args, winsync=True)
    agmt.begin_reinit()
    log.info("Agreement initialization started...")


def check_winsync_init_agmt(inst, basedn, log, args):
    agmt = get_agmt(inst, args, winsync=True)
    (done, inprogress, error) = agmt.check_reinit()
    status = "Unknown"
    if done:
        status = "Agreement successfully initialized."
    elif inprogress:
        status = "Agreement initialization in progress."
    elif error:
        status = "Agreement initialization failed."
    if args.json:
        log.info(json.dumps(status))
    else:
        log.info(status)


def get_winsync_agmt(inst, basedn, log, args):
    agmt = get_agmt(inst, args, winsync=True)
    if args.json:
        log.info(agmt.get_all_attrs_json())
    else:
        log.info(agmt.display())


def poke_winsync_agmt(inst, basedn, log, args):
    # Send updates now
    agmt = get_agmt(inst, args, winsync=True)
    agmt.pause()
    agmt.resume()
    log.info("Agreement has been poked")


def get_winsync_agmt_status(inst, basedn, log, args):
    agmt = get_agmt(inst, args, winsync=True)
    status = agmt.status(winsync=True, use_json=args.json)
    log.info(status)


#
# Tasks
#
def run_cleanallruv(inst, basedn, log, args):
    properties = {'replica-base-dn': args.suffix,
                  'replica-id': args.replica_id}
    if args.force_cleaning:
        properties['replica-force-cleaning'] = 'yes'
    clean_task = CleanAllRUVTask(inst)
    clean_task.create(properties=properties)
    rdn = clean_task.rdn
    if args.json:
        log.info(json.dumps(rdn))
    else:
        log.info('Created task ' + rdn)


def list_cleanallruv(inst, basedn, log, args):
    tasksobj = DSLdapObjects(inst)
    tasksobj._basedn = "cn=cleanallruv, cn=tasks, cn=config"
    tasksobj._scope = ldap.SCOPE_ONELEVEL
    tasksobj._objectclasses = ['top']
    tasks = tasksobj.list()
    result = {"type": "list", "items": []}
    tasks_found = False
    for task in tasks:
        tasks_found = True
        if args.suffix is not None:
            if args.suffix.lower() != task.get_attr_val_utf8_l('replica-base-dn'):
                continue
        if args.json:
            entry = task.get_all_attrs_json()
            # Append decoded json object, because we are going to dump it later
            result['items'].append(json.loads(entry))
        else:
            log.info(task.display())
    if args.json:
        log.info(json.dumps(result))
    else:
        if not tasks_found:
            log.info("No CleanAllRUV tasks found")


def abort_cleanallruv(inst, basedn, log, args):
    properties = {'replica-base-dn': args.suffix,
                  'replica-id': args.replica_id}
    if args.certify:
        properties['replica-certify-all'] = 'yes'
    clean_task = AbortCleanAllRUVTask(inst)
    clean_task.create(properties=properties)


def list_abort_cleanallruv(inst, basedn, log, args):
    tasksobj = DSLdapObjects(inst)
    tasksobj._basedn = "cn=abort cleanallruv, cn=tasks, cn=config"
    tasksobj._scope = ldap.SCOPE_ONELEVEL
    tasksobj._objectclasses = ['top']
    tasks = tasksobj.list()
    result = {"type": "list", "items": []}
    tasks_found = False
    for task in tasks:
        tasks_found = True
        if args.suffix is not None:
            if args.suffix.lower() != task.get_attr_val_utf8_l('replica-base-dn'):
                continue
        if args.json:
            entry = task.get_all_attrs_json()
            # Append decoded json object, because we are going to dump it later
            result['items'].append(json.loads(entry))
        else:
            log.info(task.display())
    if args.json:
        log.info(json.dumps(result))
    else:
        if not tasks_found:
            log.info("No CleanAllRUV abort tasks found")


def create_parser(subparsers):

    ############################################
    # Replication Configuration
    ############################################

    repl_parser = subparsers.add_parser('replication', help='Configure replication for a suffix')
    repl_subcommands = repl_parser.add_subparsers(help='Replication Configuration')

    repl_enable_parser = repl_subcommands.add_parser('enable', help='Enable replication for a suffix')
    repl_enable_parser.set_defaults(func=enable_replication)
    repl_enable_parser.add_argument('--suffix', required=True, help='The DN of the suffix to be enabled for replication')
    repl_enable_parser.add_argument('--role', required=True, help="The Replication role: \"master\", \"hub\", or \"consumer\"")
    repl_enable_parser.add_argument('--replica-id', help="The replication identifier for a \"master\".  Values range from 1 - 65534")
    repl_enable_parser.add_argument('--bind-group-dn', help="A group entry DN containing members that are \"bind/supplier\" DNs")
    repl_enable_parser.add_argument('--bind-dn', help="The Bind or Supplier DN that can make replication updates")
    repl_enable_parser.add_argument('--bind-passwd', help="Password for replication manager(--bind-dn).  This will create the manager entry if a value is set")

    repl_disable_parser = repl_subcommands.add_parser('disable', help='Disable replication for a suffix')
    repl_disable_parser.set_defaults(func=disable_replication)
    repl_disable_parser.add_argument('--suffix', required=True, help='The DN of the suffix to have replication disabled')

    repl_list_parser = repl_subcommands.add_parser('list', help='List all the replicated suffixes')
    repl_list_parser.set_defaults(func=list_suffixes)

    repl_status_parser = repl_subcommands.add_parser('status', help='Get the current status of all the replication agreements')
    repl_status_parser.set_defaults(func=get_repl_status)
    repl_status_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix")
    repl_status_parser.add_argument('--bind-dn', help="The DN to use to authenticate to the consumer")
    repl_status_parser.add_argument('--bind-passwd', help="The password for the bind DN")

    repl_winsync_status_parser = repl_subcommands.add_parser('winsync-status', help='Get the current status of all the replication agreements')
    repl_winsync_status_parser.set_defaults(func=get_repl_winsync_status)
    repl_winsync_status_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix")
    repl_winsync_status_parser.add_argument('--bind-dn', help="The DN to use to authenticate to the consumer")
    repl_winsync_status_parser.add_argument('--bind-passwd', help="The password for the bind DN")

    repl_promote_parser = repl_subcommands.add_parser('promote', help='Promte replica to a Hub or Master')
    repl_promote_parser.set_defaults(func=promote_replica)
    repl_promote_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix to promote")
    repl_promote_parser.add_argument('--newrole', required=True, help='Promote this replica to a \"hub\" or \"master\"')
    repl_promote_parser.add_argument('--replica-id', help="The replication identifier for a \"master\".  Values range from 1 - 65534")
    repl_promote_parser.add_argument('--bind-group-dn', help="A group entry DN containing members that are \"bind/supplier\" DNs")
    repl_promote_parser.add_argument('--bind-dn', help="The Bind or Supplier DN that can make replication updates")

    repl_add_manager_parser = repl_subcommands.add_parser('create-manager', help='Create a replication manager entry')
    repl_add_manager_parser.set_defaults(func=create_repl_manager)
    repl_add_manager_parser.add_argument('--name', help="The NAME of the new replication manager entry.  For example, " +
                                                        "if the NAME is \"replication manager\" then the new manager " +
                                                        "entry's DN would be \"cn=replication manager,cn=config\".")
    repl_add_manager_parser.add_argument('--passwd', help="Password for replication manager.  If not provided, you will be prompted for the password")
    repl_add_manager_parser.add_argument('--suffix', help='The DN of the replication suffix whose replication ' +
                                                          'configuration you want to add this new manager to (OPTIONAL)')

    repl_del_manager_parser = repl_subcommands.add_parser('delete-manager', help='Delete a replication manager entry')
    repl_del_manager_parser.set_defaults(func=del_repl_manager)
    repl_del_manager_parser.add_argument('--name', help="The NAME of the replication manager entry under cn=config:  \"cn=NAME,cn=config\"")
    repl_del_manager_parser.add_argument('--suffix', help='The DN of the replication suffix whose replication ' +
                                                          'configuration you want to remove this manager from (OPTIONAL)')

    repl_demote_parser = repl_subcommands.add_parser('demote', help='Demote replica to a Hub or Consumer')
    repl_demote_parser.set_defaults(func=demote_replica)
    repl_demote_parser.add_argument('--suffix', required=True, help="Promte this replica to a \"hub\" or \"consumer\"")
    repl_demote_parser.add_argument('--newrole', required=True, help="The Replication role: \"hub\", or \"consumer\"")

    repl_get_parser = repl_subcommands.add_parser('get', help='Get replication configuration')
    repl_get_parser.set_defaults(func=get_repl_config)
    repl_get_parser.add_argument('--suffix', required=True, help='Get the replication configuration for this suffix DN')

    repl_create_cl = repl_subcommands.add_parser('create-changelog', help='Create the replication changelog')
    repl_create_cl.set_defaults(func=create_cl)

    repl_delete_cl = repl_subcommands.add_parser('delete-changelog', help='Delete the replication changelog.  This will invalidate any existing replication agreements')
    repl_delete_cl.set_defaults(func=delete_cl)

    repl_set_cl = repl_subcommands.add_parser('set-changelog', help='Set replication changelog attributes.')
    repl_set_cl.set_defaults(func=set_cl)
    repl_set_cl.add_argument('--cl-dir', help="The replication changelog location on the filesystem")
    repl_set_cl.add_argument('--max-entries', help="The maximum number of entries to get in the replication changelog")
    repl_set_cl.add_argument('--max-age', help="The maximum age of a replication changelog entry")
    repl_set_cl.add_argument('--compact-interval', help="The replication changelog compaction interval")
    repl_set_cl.add_argument('--trim-interval', help="The interval to check if the replication changelog can be trimmed")

    repl_get_cl = repl_subcommands.add_parser('get-changelog', help='Display replication changelog attributes.')
    repl_get_cl.set_defaults(func=get_cl)

    repl_set_parser = repl_subcommands.add_parser('set', help='Set an attribute in the replication configuration')
    repl_set_parser.set_defaults(func=set_repl_config)
    repl_set_parser.add_argument('--suffix', required=True, help='The DN of the replication suffix')
    repl_set_parser.add_argument('--replica-id', help="The Replication Identifier number")
    repl_set_parser.add_argument('--replica-role', help="The Replication role: master, hub, or consumer")

    repl_set_parser.add_argument('--repl-add-bind-dn', help="Add a bind (supplier) DN")
    repl_set_parser.add_argument('--repl-del-bind-dn', help="Remove a bind (supplier) DN")
    repl_set_parser.add_argument('--repl-add-ref', help="Add a replication referral (for consumers only)")
    repl_set_parser.add_argument('--repl-del-ref', help="Remove a replication referral (for conusmers only)")
    repl_set_parser.add_argument('--repl-purge-delay', help="The replication purge delay")
    repl_set_parser.add_argument('--repl-tombstone-purge-interval', help="The interval in seconds to check for tombstones that can be purged")
    repl_set_parser.add_argument('--repl-fast-tombstone-purging', help="Set to \"on\" to improve tombstone purging performance")
    repl_set_parser.add_argument('--repl-bind-group', help="A group entry DN containing members that are \"bind/supplier\" DNs")
    repl_set_parser.add_argument('--repl-bind-group-interval', help="An interval in seconds to check if the bind group has been updated")
    repl_set_parser.add_argument('--repl-protocol-timeout', help="A timeout in seconds on how long to wait before stopping "
                                                                 "replication when the server is under load")
    repl_set_parser.add_argument('--repl-backoff-max', help="The maximum time in seconds a replication agreement should stay in a backoff state "
                                                            "while waiting to acquire the consumer.  Default is 300 seconds")
    repl_set_parser.add_argument('--repl-backoff-min', help="The starting time in seconds a replication agreement should stay in a backoff state "
                                                            "while waiting to acquire the consumer.  Default is 3 seconds")
    repl_set_parser.add_argument('--repl-release-timeout', help="A timeout in seconds a replication master should send "
                                                                "updates before it yields its replication session")

    ############################################
    # Replication Agmts
    ############################################

    agmt_parser = subparsers.add_parser('repl-agmt', help='Manage replication agreements')
    agmt_subcommands = agmt_parser.add_subparsers(help='Replication Agreement Configuration')

    # List
    agmt_list_parser = agmt_subcommands.add_parser('list', help='List all the replication agreements')
    agmt_list_parser.set_defaults(func=list_agmts)
    agmt_list_parser.add_argument('--suffix', required=True, help='The DN of the suffix to look up replication agreements')
    agmt_list_parser.add_argument('--entry', help='Return the entire entry for each agreement')

    # Enable
    agmt_enable_parser = agmt_subcommands.add_parser('enable', help='Enable replication agreement')
    agmt_enable_parser.set_defaults(func=enable_agmt)
    agmt_enable_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication agreement')
    agmt_enable_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix")

    # Disable
    agmt_disable_parser = agmt_subcommands.add_parser('disable', help='Disable replication agreement')
    agmt_disable_parser.set_defaults(func=disable_agmt)
    agmt_disable_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication agreement')
    agmt_disable_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix")

    # Initialize
    agmt_init_parser = agmt_subcommands.add_parser('init', help='Initialize replication agreement')
    agmt_init_parser.set_defaults(func=init_agmt)
    agmt_init_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication agreement')
    agmt_init_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix")

    # Check Initialization progress
    agmt_check_init_parser = agmt_subcommands.add_parser('init-status', help='Check the agreement initialization status')
    agmt_check_init_parser.set_defaults(func=check_init_agmt)
    agmt_check_init_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication agreement')
    agmt_check_init_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix")

    # Send Updates Now
    agmt_poke_parser = agmt_subcommands.add_parser('poke', help='Trigger replication to send updates now')
    agmt_poke_parser.set_defaults(func=poke_agmt)
    agmt_poke_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication agreement')
    agmt_poke_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix")

    # Status
    agmt_status_parser = agmt_subcommands.add_parser('status', help='Get the current status of the replication agreement')
    agmt_status_parser.set_defaults(func=get_agmt_status)
    agmt_status_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication agreement')
    agmt_status_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix")
    agmt_status_parser.add_argument('--bind-dn', help="The DN to use to authenticate to the consumer")
    agmt_status_parser.add_argument('--bind-passwd', help="The password for the bind DN")

    # Delete
    agmt_del_parser = agmt_subcommands.add_parser('delete', help='Delete replication agreement')
    agmt_del_parser.set_defaults(func=delete_agmt)
    agmt_del_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication agreement')
    agmt_del_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix")

    # Create
    agmt_add_parser = agmt_subcommands.add_parser('create', help='Initialize replication agreement')
    agmt_add_parser.set_defaults(func=add_agmt)
    agmt_add_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication agreement')
    agmt_add_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix")
    agmt_add_parser.add_argument('--host', required=True, help="The hostname of the remote replica")
    agmt_add_parser.add_argument('--port', required=True, help="The port number of the remote replica")
    agmt_add_parser.add_argument('--conn-protocol', required=True, help="The replication connection protocol: LDAP, LDAPS, or StartTLS")
    agmt_add_parser.add_argument('--bind-dn', help="The Bind DN the agreement uses to authenticate to the replica")
    agmt_add_parser.add_argument('--bind-passwd', help="The credentials for the Bind DN")
    agmt_add_parser.add_argument('--bind-method', required=True, help="The bind method: \"SIMPLE\", \"SSLCLIENTAUTH\", \"SASL/DIGEST\", or \"SASL/GSSAPI\"")
    agmt_add_parser.add_argument('--frac-list', help="List of attributes to NOT replicate to the consumer during incremental updates")
    agmt_add_parser.add_argument('--frac-list-total', help="List of attributes to NOT replicate during a total initialization")
    agmt_add_parser.add_argument('--strip-list', help="A list of attributes that are removed from updates only if the event "
                                                      "would otherwise be empty.  Typically this is set to \"modifiersname\" and \"modifytimestmap\"")
    agmt_add_parser.add_argument('--schedule', help="Sets the replication update schedule: 'HHMM-HHMM DDDDDDD'  D = 0-6 (Sunday - Saturday).")
    agmt_add_parser.add_argument('--conn-timeout', help="The timeout used for replicaton connections")
    agmt_add_parser.add_argument('--protocol-timeout', help="A timeout in seconds on how long to wait before stopping "
                                                            "replication when the server is under load")
    agmt_add_parser.add_argument('--wait-async-results', help="The amount of time in milliseconds the server waits if "
                                                              "the consumer is not ready before resending data")
    agmt_add_parser.add_argument('--busy-wait-time', help="The amount of time in seconds a supplier should wait after "
                                                          "a consumer sends back a busy response before making another "
                                                          "attempt to acquire access.")
    agmt_add_parser.add_argument('--session-pause-time', help="The amount of time in seconds a supplier should wait between update sessions.")
    agmt_add_parser.add_argument('--flow-control-window', help="Sets the maximum number of entries and updates sent by a supplier, which are not acknowledged by the consumer.")
    agmt_add_parser.add_argument('--flow-control-pause', help="The time in milliseconds to pause after reaching the number of entries and updates set in \"--flow-control-window\"")
    agmt_add_parser.add_argument('--init', action='store_true', default=False, help="Initialize the agreement after creating it.")

    # Set - Note can not use add's parent args because for "set" there are no "required=True" args
    agmt_set_parser = agmt_subcommands.add_parser('set', help='Set an attribute in the replication agreement')
    agmt_set_parser.set_defaults(func=set_agmt)
    agmt_set_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication agreement')
    agmt_set_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix")
    agmt_set_parser.add_argument('--host', help="The hostname of the remote replica")
    agmt_set_parser.add_argument('--port', help="The port number of the remote replica")
    agmt_set_parser.add_argument('--conn-protocol', help="The replication connection protocol: LDAP, LDAPS, or StartTLS")
    agmt_set_parser.add_argument('--bind-dn', help="The Bind DN the agreement uses to authenticate to the replica")
    agmt_set_parser.add_argument('--bind-passwd', help="The credentials for the Bind DN")
    agmt_set_parser.add_argument('--bind-method', help="The bind method: \"SIMPLE\", \"SSLCLIENTAUTH\", \"SASL/DIGEST\", or \"SASL/GSSAPI\"")
    agmt_set_parser.add_argument('--frac-list', help="List of attributes to NOT replicate to the consumer during incremental updates")
    agmt_set_parser.add_argument('--frac-list-total', help="List of attributes to NOT replicate during a total initialization")
    agmt_set_parser.add_argument('--strip-list', help="A list of attributes that are removed from updates only if the event "
                                                      "would otherwise be empty.  Typically this is set to \"modifiersname\" and \"modifytimestmap\"")
    agmt_set_parser.add_argument('--schedule', help="Sets the replication update schedule: 'HHMM-HHMM DDDDDDD'  D = 0-6 (Sunday - Saturday).")
    agmt_set_parser.add_argument('--conn-timeout', help="The timeout used for replicaton connections")
    agmt_set_parser.add_argument('--protocol-timeout', help="A timeout in seconds on how long to wait before stopping "
                                                            "replication when the server is under load")
    agmt_set_parser.add_argument('--wait-async-results', help="The amount of time in milliseconds the server waits if "
                                                              "the consumer is not ready before resending data")
    agmt_set_parser.add_argument('--busy-wait-time', help="The amount of time in seconds a supplier should wait after "
                                                          "a consumer sends back a busy response before making another "
                                                          "attempt to acquire access.")
    agmt_set_parser.add_argument('--session-pause-time', help="The amount of time in seconds a supplier should wait between update sessions.")
    agmt_set_parser.add_argument('--flow-control-window', help="Sets the maximum number of entries and updates sent by a supplier, which are not acknowledged by the consumer.")
    agmt_set_parser.add_argument('--flow-control-pause', help="The time in milliseconds to pause after reaching the number of entries and updates set in \"--flow-control-window\"")

    # Get
    agmt_get_parser = agmt_subcommands.add_parser('get', help='Get replication configuration')
    agmt_get_parser.set_defaults(func=get_repl_agmt)
    agmt_get_parser.add_argument('AGMT_NAME', nargs=1, help='Get the replication configuration for this suffix DN')
    agmt_get_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix")

    ############################################
    # Replication Winsync Agmts
    ############################################

    winsync_parser = subparsers.add_parser('repl-winsync-agmt', help='Manage Winsync Agreements')
    winsync_agmt_subcommands = winsync_parser.add_subparsers(help='Replication Winsync Agreement Configuration')

    # List
    winsync_agmt_list_parser = winsync_agmt_subcommands.add_parser('list', help='List all the replication winsync agreements')
    winsync_agmt_list_parser.set_defaults(func=list_winsync_agmts)
    winsync_agmt_list_parser.add_argument('--suffix', required=True, help='The DN of the suffix to look up replication winsync agreements')

    # Enable
    winsync_agmt_enable_parser = winsync_agmt_subcommands.add_parser('enable', help='Enable replication winsync agreement')
    winsync_agmt_enable_parser.set_defaults(func=enable_winsync_agmt)
    winsync_agmt_enable_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication winsync agreement')
    winsync_agmt_enable_parser.add_argument('--suffix', required=True, help="The DN of the replication winsync suffix")

    # Disable
    winsync_agmt_disable_parser = winsync_agmt_subcommands.add_parser('disable', help='Disable replication winsync agreement')
    winsync_agmt_disable_parser.set_defaults(func=disable_winsync_agmt)
    winsync_agmt_disable_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication winsync agreement')
    winsync_agmt_disable_parser.add_argument('--suffix', required=True, help="The DN of the replication winsync suffix")

    # Initialize
    winsync_agmt_init_parser = winsync_agmt_subcommands.add_parser('init', help='Initialize replication winsync agreement')
    winsync_agmt_init_parser.set_defaults(func=init_winsync_agmt)
    winsync_agmt_init_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication winsync agreement')
    winsync_agmt_init_parser.add_argument('--suffix', required=True, help="The DN of the replication winsync suffix")

    # Check Initialization progress
    winsync_agmt_check_init_parser = winsync_agmt_subcommands.add_parser('init-status', help='Check the agreement initialization status')
    winsync_agmt_check_init_parser.set_defaults(func=check_winsync_init_agmt)
    winsync_agmt_check_init_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication agreement')
    winsync_agmt_check_init_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix")

    # Send Updates Now
    winsync_agmt_poke_parser = winsync_agmt_subcommands.add_parser('poke', help='Trigger replication to send updates now')
    winsync_agmt_poke_parser.set_defaults(func=poke_winsync_agmt)
    winsync_agmt_poke_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication winsync agreement')
    winsync_agmt_poke_parser.add_argument('--suffix', required=True, help="The DN of the replication winsync suffix")

    # Status
    winsync_agmt_status_parser = winsync_agmt_subcommands.add_parser('status', help='Get the current status of the replication agreement')
    winsync_agmt_status_parser.set_defaults(func=get_winsync_agmt_status)
    winsync_agmt_status_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication agreement')
    winsync_agmt_status_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix")

    # Delete
    winsync_agmt_del_parser = winsync_agmt_subcommands.add_parser('delete', help='Delete replication winsync agreement')
    winsync_agmt_del_parser.set_defaults(func=delete_winsync_agmt)
    winsync_agmt_del_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication winsync agreement')
    winsync_agmt_del_parser.add_argument('--suffix', required=True, help="The DN of the replication winsync suffix")

    # Create
    winsync_agmt_add_parser = winsync_agmt_subcommands.add_parser('create', help='Initialize replication winsync agreement')
    winsync_agmt_add_parser.set_defaults(func=add_winsync_agmt)
    winsync_agmt_add_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication winsync agreement')
    winsync_agmt_add_parser.add_argument('--suffix', required=True, help="The DN of the replication winsync suffix")
    winsync_agmt_add_parser.add_argument('--host', required=True, help="The hostname of the AD server")
    winsync_agmt_add_parser.add_argument('--port', required=True, help="The port number of the AD server")
    winsync_agmt_add_parser.add_argument('--conn-protocol', required=True, help="The replication winsync connection protocol: LDAP, LDAPS, or StartTLS")
    winsync_agmt_add_parser.add_argument('--bind-dn', required=True, help="The Bind DN the agreement uses to authenticate to the AD Server")
    winsync_agmt_add_parser.add_argument('--bind-passwd', required=True, help="The credentials for the Bind DN")
    winsync_agmt_add_parser.add_argument('--frac-list', help="List of attributes to NOT replicate to the consumer during incremental updates")
    winsync_agmt_add_parser.add_argument('--schedule', help="Sets the replication update schedule")
    winsync_agmt_add_parser.add_argument('--win-subtree', required=True, help="The suffix of the AD Server")
    winsync_agmt_add_parser.add_argument('--ds-subtree', required=True, help="The Directory Server suffix")
    winsync_agmt_add_parser.add_argument('--win-domain', required=True, help="The AD Domain")
    winsync_agmt_add_parser.add_argument('--sync-users', help="Synchronize Users between AD and DS")
    winsync_agmt_add_parser.add_argument('--sync-groups', help="Synchronize Groups between AD and DS")
    winsync_agmt_add_parser.add_argument('--sync-interval', help="The interval that DS checks AD for changes in entries")
    winsync_agmt_add_parser.add_argument('--one-way-sync', help="Sets which direction to perform synchronization: \"toWindows\", \"fromWindows\", \"both\"")
    winsync_agmt_add_parser.add_argument('--move-action', help="Sets instructions on how to handle moved or deleted entries: \"none\", \"unsync\", or \"delete\"")
    winsync_agmt_add_parser.add_argument('--win-filter', help="Custom filter for finding users in AD Server")
    winsync_agmt_add_parser.add_argument('--ds-filter', help="Custom filter for finding AD users in DS Server")
    winsync_agmt_add_parser.add_argument('--subtree-pair', help="Set the subtree pair: <DS_SUBTREE>:<WINDOWS_SUBTREE>")
    winsync_agmt_add_parser.add_argument('--conn-timeout', help="The timeout used for replicaton connections")
    winsync_agmt_add_parser.add_argument('--busy-wait-time', help="The amount of time in seconds a supplier should wait after "
                                                          "a consumer sends back a busy response before making another "
                                                          "attempt to acquire access.")
    winsync_agmt_add_parser.add_argument('--session-pause-time', help="The amount of time in seconds a supplier should wait between update sessions.")
    winsync_agmt_add_parser.add_argument('--init', action='store_true', default=False, help="Initialize the agreement after creating it.")

    # Set - Note can not use add's parent args because for "set" there are no "required=True" args
    winsync_agmt_set_parser = winsync_agmt_subcommands.add_parser('set', help='Set an attribute in the replication winsync agreement')
    winsync_agmt_set_parser.set_defaults(func=set_winsync_agmt)
    winsync_agmt_set_parser.add_argument('AGMT_NAME', nargs=1, help='The name of the replication winsync agreement')
    winsync_agmt_set_parser.add_argument('--suffix', help="The DN of the replication winsync suffix")
    winsync_agmt_set_parser.add_argument('--host', help="The hostname of the AD server")
    winsync_agmt_set_parser.add_argument('--port', help="The port number of the AD server")
    winsync_agmt_set_parser.add_argument('--conn-protocol', help="The replication winsync connection protocol: LDAP, LDAPS, or StartTLS")
    winsync_agmt_set_parser.add_argument('--bind-dn', help="The Bind DN the agreement uses to authenticate to the AD Server")
    winsync_agmt_set_parser.add_argument('--bind-passwd', help="The credentials for the Bind DN")
    winsync_agmt_set_parser.add_argument('--frac-list', help="List of attributes to NOT replicate to the consumer during incremental updates")
    winsync_agmt_set_parser.add_argument('--schedule', help="Sets the replication update schedule")
    winsync_agmt_set_parser.add_argument('--win-subtree', help="The suffix of the AD Server")
    winsync_agmt_set_parser.add_argument('--ds-subtree', help="The Directory Server suffix")
    winsync_agmt_set_parser.add_argument('--win-domain', help="The AD Domain")
    winsync_agmt_set_parser.add_argument('--sync-users', help="Synchronize Users between AD and DS")
    winsync_agmt_set_parser.add_argument('--sync-groups', help="Synchronize Groups between AD and DS")
    winsync_agmt_set_parser.add_argument('--sync-interval', help="The interval that DS checks AD for changes in entries")
    winsync_agmt_set_parser.add_argument('--one-way-sync', help="Sets which direction to perform synchronization: \"toWindows\", \"fromWindows\", \"both\"")
    winsync_agmt_set_parser.add_argument('--move-action', help="Sets instructions on how to handle moved or deleted entries: \"none\", \"unsync\", or \"delete\"")
    winsync_agmt_set_parser.add_argument('--win-filter', help="Custom filter for finding users in AD Server")
    winsync_agmt_set_parser.add_argument('--ds-filter', help="Custom filter for finding AD users in DS Server")
    winsync_agmt_set_parser.add_argument('--subtree-pair', help="Set the subtree pair: <DS_SUBTREE>:<WINDOWS_SUBTREE>")
    winsync_agmt_set_parser.add_argument('--conn-timeout', help="The timeout used for replicaton connections")
    winsync_agmt_set_parser.add_argument('--busy-wait-time', help="The amount of time in seconds a supplier should wait after "
                                                          "a consumer sends back a busy response before making another "
                                                          "attempt to acquire access.")
    winsync_agmt_set_parser.add_argument('--session-pause-time', help="The amount of time in seconds a supplier should wait between update sessions.")

    # Get
    winsync_agmt_get_parser = winsync_agmt_subcommands.add_parser('get', help='Get replication configuration')
    winsync_agmt_get_parser.set_defaults(func=get_winsync_agmt)
    winsync_agmt_get_parser.add_argument('AGMT_NAME', nargs=1, help='Get the replication configuration for this suffix DN')
    winsync_agmt_get_parser.add_argument('--suffix', required=True, help="The DN of the replication suffix")

    ############################################
    # Replication Tasks (cleanalruv)
    ############################################

    tasks_parser = subparsers.add_parser('repl-tasks', help='Manage replication tasks')
    task_subcommands = tasks_parser.add_subparsers(help='Replication Tasks')

    # Cleanallruv
    task_cleanallruv = task_subcommands.add_parser('cleanallruv', help='Cleanup old/removed replica IDs')
    task_cleanallruv.set_defaults(func=run_cleanallruv)
    task_cleanallruv.add_argument('--suffix', required=True, help="The Directory Server suffix")
    task_cleanallruv.add_argument('--replica-id', required=True, help="The replica ID to remove/clean")
    task_cleanallruv.add_argument('--force-cleaning', action='store_true', default=False,
                                  help="Ignore errors and do a best attempt to clean all the replicas")

    task_cleanallruv_list = task_subcommands.add_parser('list-cleanruv-tasks', help='List all the running CleanAllRUV tasks')
    task_cleanallruv_list.set_defaults(func=list_cleanallruv)
    task_cleanallruv_list.add_argument('--suffix', help="List only tasks from for suffix")

    # Abort cleanallruv
    task_abort_cleanallruv = task_subcommands.add_parser('abort-cleanallruv', help='Abort cleanallruv tasks')
    task_abort_cleanallruv.set_defaults(func=abort_cleanallruv)
    task_abort_cleanallruv.add_argument('--suffix', required=True, help="The Directory Server suffix")
    task_abort_cleanallruv.add_argument('--replica-id', required=True, help="The replica ID of the cleaning task to abort")
    task_abort_cleanallruv.add_argument('--certify', action='store_true', default=False,
                                        help="Enforce that the abort task completed on all replicas")

    task_abort_cleanallruv_list = task_subcommands.add_parser('list-abortruv-tasks', help='List all the running CleanAllRUV abort Tasks')
    task_abort_cleanallruv_list.set_defaults(func=list_abort_cleanallruv)
    task_abort_cleanallruv_list.add_argument('--suffix', help="List only tasks from for suffix")

