import cockpit from "cockpit";
import React from "react";
import PropTypes from "prop-types";
import { log_cmd } from "./lib/tools.jsx";
import { Col, Row, Tab, Nav, NavItem, Spinner } from "patternfly-react";
import PluginEditModal from "./lib/plugins/pluginModal.jsx";
import { PluginTable } from "./lib/plugins/pluginTables.jsx";
import AccountPolicy from "./lib/plugins/accountPolicy.jsx";
import AttributeUniqueness from "./lib/plugins/attributeUniqueness.jsx";
import AutoMembership from "./lib/plugins/autoMembership.jsx";
import DNA from "./lib/plugins/dna.jsx";
import LinkedAttributes from "./lib/plugins/linkedAttributes.jsx";
import ManagedEntries from "./lib/plugins/managedEntries.jsx";
import MemberOf from "./lib/plugins/memberOf.jsx";
import PassthroughAuthentication from "./lib/plugins/passthroughAuthentication.jsx";
import ReferentialIntegrity from "./lib/plugins/referentialIntegrity.jsx";
import RetroChangelog from "./lib/plugins/retroChangelog.jsx";
import RootDNAccessControl from "./lib/plugins/rootDNAccessControl.jsx";
import USN from "./lib/plugins/usn.jsx";
import WinSync from "./lib/plugins/winsync.jsx";
import { NotificationController } from "./lib/notifications.jsx";
import "./css/ds.css";

var cmd;

export class Plugins extends React.Component {
    componentWillMount() {
        this.pluginList();
        this.setState(prevState => ({
            pluginTabs: {
                ...prevState.pluginTabs,
                basicConfig: true
            }
        }));
    }

    componentDidUpdate(prevProps) {
        if (this.props.serverId !== prevProps.serverId) {
            this.pluginList();
        }
    }

    constructor() {
        super();

        this.handleFieldChange = this.handleFieldChange.bind(this);
        this.handleSwitchChange = this.handleSwitchChange.bind(this);
        this.openPluginModal = this.openPluginModal.bind(this);
        this.closePluginModal = this.closePluginModal.bind(this);
        this.pluginList = this.pluginList.bind(this);
        this.removeNotification = this.removeNotification.bind(this);
        this.addNotification = this.addNotification.bind(this);
        this.onChangeTab = this.onChangeTab.bind(this);
        this.savePlugin = this.savePlugin.bind(this);
        this.toggleLoading = this.toggleLoading.bind(this);

        this.state = {
            notifications: [],
            loading: false,
            showPluginModal: false,
            currentPluginTab: "",
            rows: [],

            // Plugin attributes
            currentPluginName: "",
            currentPluginType: "",
            currentPluginEnabled: false,
            currentPluginPath: "",
            currentPluginInitfunc: "",
            currentPluginId: "",
            currentPluginVendor: "",
            currentPluginVersion: "",
            currentPluginDescription: "",
            currentPluginDependsOnType: "",
            currentPluginDependsOnNamed: "",
            currentPluginPrecedence: ""
        };
    }

    onChangeTab(event) {
        this.setState({ currentPluginTab: event.target.value });
    }

    addNotification(type, message, timerdelay, persistent) {
        this.setState(prevState => ({
            notifications: [
                ...prevState.notifications,
                {
                    key: prevState.notifications.length + 1,
                    type: type,
                    persistent: persistent,
                    timerdelay: timerdelay,
                    message: message
                }
            ]
        }));
    }

    removeNotification(notificationToRemove) {
        this.setState({
            notifications: this.state.notifications.filter(
                notification => notificationToRemove.key !== notification.key
            )
        });
    }

    handleFieldChange(e) {
        this.setState({
            [e.target.id]: e.target.value
        });
    }

    handleSwitchChange(value) {
        this.setState({
            currentPluginEnabled: !value
        });
    }

    closePluginModal() {
        this.setState({
            showPluginModal: false
        });
    }

    toggleLoading() {
        this.setState(prevState => ({
            loading: !prevState.loading
        }));
    }

    openPluginModal(rowData) {
        var pluginEnabled;
        if (rowData["nsslapd-pluginEnabled"][0] === "on") {
            pluginEnabled = true;
        } else if (rowData["nsslapd-pluginEnabled"][0] === "off") {
            pluginEnabled = false;
        } else {
            console.error(
                "openPluginModal failed",
                "wrong nsslapd-pluginenabled attribute value",
                rowData["nsslapd-pluginEnabled"][0]
            );
        }
        this.setState({
            currentPluginName: rowData.cn[0],
            currentPluginType: rowData["nsslapd-pluginType"][0],
            currentPluginEnabled: pluginEnabled,
            currentPluginPath: rowData["nsslapd-pluginPath"][0],
            currentPluginInitfunc: rowData["nsslapd-pluginInitfunc"][0],
            currentPluginId: rowData["nsslapd-pluginId"][0],
            currentPluginVendor: rowData["nsslapd-pluginVendor"][0],
            currentPluginVersion: rowData["nsslapd-pluginVersion"][0],
            currentPluginDescription: rowData["nsslapd-pluginDescription"][0],
            currentPluginDependsOnType:
                rowData["nsslapd-plugin-depends-on-type"] === undefined
                    ? ""
                    : rowData["nsslapd-plugin-depends-on-type"][0],
            currentPluginDependsOnNamed:
                rowData["nsslapd-plugin-depends-on-named"] === undefined
                    ? ""
                    : rowData["nsslapd-plugin-depends-on-named"][0],
            currentPluginPrecedence:
                rowData["nsslapd-pluginprecedence"] === undefined
                    ? ""
                    : rowData["nsslapd-pluginprecedence"][0],
            showPluginModal: true
        });
    }

    pluginList() {
        cmd = [
            "dsconf",
            "-j",
            "ldapi://%2fvar%2frun%2fslapd-" + this.props.serverId + ".socket",
            "plugin",
            "list"
        ];
        this.toggleLoading();
        log_cmd("pluginList", "Get plugins for table rows", cmd);
        cockpit
                .spawn(cmd, { superuser: true, err: "message" })
                .done(content => {
                    var myObject = JSON.parse(content);
                    this.setState({
                        rows: myObject.items
                    });
                    this.toggleLoading();
                })
                .fail(err => {
                    if (err != 0) {
                        let errMsg = JSON.parse(err);
                        console.log("pluginList failed: ", errMsg.desc);
                    }
                    this.toggleLoading();
                });
    }

    savePlugin(data) {
        let nothingToSetErr = false;
        let basicPluginSuccess = false;
        let cmd = [
            "dsconf",
            "-j",
            "ldapi://%2fvar%2frun%2fslapd-" + this.props.serverId + ".socket",
            "plugin",
            "set",
            data.name,
            "--type",
            data.type || "delete",
            "--path",
            data.path || "delete",
            "--initfunc",
            data.initfunc || "delete",
            "--id",
            data.id || "delete",
            "--vendor",
            data.vendor || "delete",
            "--version",
            data.version || "delete",
            "--description",
            data.description || "delete",
            "--depends-on-type",
            data.dependsOnType || "delete",
            "--depends-on-named",
            data.dependsOnNamed || "delete",
            "--precedence",
            data.precedence || "delete"
        ];

        if ("enabled" in data) {
            cmd = [...cmd, "--enabled", data.enabled ? "on" : "off"];
        }

        this.toggleLoading();

        log_cmd("savePlugin", "Edit the plugin", cmd);
        cockpit
                .spawn(cmd, { superuser: true, err: "message" })
                .done(content => {
                    console.info("savePlugin", "Result", content);
                    basicPluginSuccess = true;
                    this.addNotification("success", `Plugin ${data.name} was successfully modified`);
                    this.pluginList();
                    this.closePluginModal();
                    this.toggleLoading();
                })
                .fail(err => {
                    let errMsg = JSON.parse(err);
                    if (errMsg.desc.indexOf("nothing to set") >= 0) {
                        nothingToSetErr = true;
                    } else {
                        this.addNotification(
                            "error",
                            `${errMsg.desc} error during ${data.name} modification`
                        );
                    }
                    this.closePluginModal();
                    this.toggleLoading();
                })
                .always(() => {
                    if ("specificPluginCMD" in data && data.specificPluginCMD.length != 0) {
                        this.toggleLoading();
                        log_cmd(
                            "savePlugin",
                            "Edit the plugin from the plugin config tab",
                            data.specificPluginCMD
                        );
                        cockpit
                                .spawn(data.specificPluginCMD, {
                                    superuser: true,
                                    err: "message"
                                })
                                .done(content => {
                                    // Notify success only one time
                                    if (!basicPluginSuccess) {
                                        this.addNotification(
                                            "success",
                                            `Plugin ${data.name} was successfully modified`
                                        );
                                    }
                                    this.pluginList();
                                    this.toggleLoading();
                                    console.info("savePlugin", "Result", content);
                                })
                                .fail(err => {
                                    let errMsg = JSON.parse(err);
                                    if (
                                        (errMsg.desc.indexOf("nothing to set") >= 0 && nothingToSetErr) ||
                                errMsg.desc.indexOf("nothing to set") < 0
                                    ) {
                                        if (basicPluginSuccess) {
                                            this.addNotification(
                                                "success",
                                                `Plugin ${data.name} was successfully modified`
                                            );
                                            this.pluginList();
                                        }
                                        this.addNotification(
                                            "error",
                                            `${errMsg.desc} error during ${data.name} modification`
                                        );
                                    }
                                    this.toggleLoading();
                                });
                    } else {
                        this.pluginList();
                    }
                });
    }

    render() {
        const selectPlugins = {
            allPlugins: {
                name: "All Plugins",
                component: (
                    <PluginTable rows={this.state.rows} loadModalHandler={this.openPluginModal} />
                )
            },
            accountPolicy: {
                name: "Account Policy",
                component: (
                    <AccountPolicy
                        rows={this.state.rows}
                        serverId={this.props.serverId}
                        savePluginHandler={this.savePlugin}
                        pluginListHandler={this.pluginList}
                        addNotification={this.addNotification}
                        toggleLoadingHandler={this.toggleLoading}
                    />
                )
            },
            attributeUniqueness: {
                name: "Attribute Uniqueness",
                component: (
                    <AttributeUniqueness
                        rows={this.state.rows}
                        serverId={this.props.serverId}
                        savePluginHandler={this.savePlugin}
                        pluginListHandler={this.pluginList}
                        addNotification={this.addNotification}
                        toggleLoadingHandler={this.toggleLoading}
                    />
                )
            },
            linkedAttributes: {
                name: "Linked Attributes",
                component: (
                    <LinkedAttributes
                        rows={this.state.rows}
                        serverId={this.props.serverId}
                        savePluginHandler={this.savePlugin}
                        pluginListHandler={this.pluginList}
                        addNotification={this.addNotification}
                        toggleLoadingHandler={this.toggleLoading}
                    />
                )
            },
            dna: {
                name: "DNA",
                component: (
                    <DNA
                        rows={this.state.rows}
                        serverId={this.props.serverId}
                        savePluginHandler={this.savePlugin}
                        pluginListHandler={this.pluginList}
                        addNotification={this.addNotification}
                        toggleLoadingHandler={this.toggleLoading}
                    />
                )
            },
            autoMembership: {
                name: "Auto Membership",
                component: (
                    <AutoMembership
                        rows={this.state.rows}
                        serverId={this.props.serverId}
                        savePluginHandler={this.savePlugin}
                        pluginListHandler={this.pluginList}
                        addNotification={this.addNotification}
                        toggleLoadingHandler={this.toggleLoading}
                    />
                )
            },
            memberOf: {
                name: "MemberOf",
                component: (
                    <MemberOf
                        rows={this.state.rows}
                        serverId={this.props.serverId}
                        savePluginHandler={this.savePlugin}
                        pluginListHandler={this.pluginList}
                        addNotification={this.addNotification}
                        toggleLoadingHandler={this.toggleLoading}
                    />
                )
            },
            managedEntries: {
                name: "Managed Entries",
                component: (
                    <ManagedEntries
                        rows={this.state.rows}
                        serverId={this.props.serverId}
                        savePluginHandler={this.savePlugin}
                        pluginListHandler={this.pluginList}
                        addNotification={this.addNotification}
                        toggleLoadingHandler={this.toggleLoading}
                    />
                )
            },
            passthroughAuthentication: {
                name: "Passthrough Authentication",
                component: (
                    <PassthroughAuthentication
                        rows={this.state.rows}
                        serverId={this.props.serverId}
                        savePluginHandler={this.savePlugin}
                        pluginListHandler={this.pluginList}
                        addNotification={this.addNotification}
                        toggleLoadingHandler={this.toggleLoading}
                    />
                )
            },
            winsync: {
                name: "Posix Winsync",
                component: (
                    <WinSync
                        rows={this.state.rows}
                        serverId={this.props.serverId}
                        savePluginHandler={this.savePlugin}
                        pluginListHandler={this.pluginList}
                        addNotification={this.addNotification}
                        toggleLoadingHandler={this.toggleLoading}
                    />
                )
            },
            referentialIntegrity: {
                name: "Referential Integrity",
                component: (
                    <ReferentialIntegrity
                        rows={this.state.rows}
                        serverId={this.props.serverId}
                        savePluginHandler={this.savePlugin}
                        pluginListHandler={this.pluginList}
                        addNotification={this.addNotification}
                        toggleLoadingHandler={this.toggleLoading}
                    />
                )
            },
            retroChangelog: {
                name: "Retro Changelog",
                component: (
                    <RetroChangelog
                        rows={this.state.rows}
                        serverId={this.props.serverId}
                        savePluginHandler={this.savePlugin}
                        pluginListHandler={this.pluginList}
                        addNotification={this.addNotification}
                        toggleLoadingHandler={this.toggleLoading}
                    />
                )
            },
            rootDnaAccessControl: {
                name: "RootDN Access Control",
                component: (
                    <RootDNAccessControl
                        rows={this.state.rows}
                        serverId={this.props.serverId}
                        savePluginHandler={this.savePlugin}
                        pluginListHandler={this.pluginList}
                        addNotification={this.addNotification}
                        toggleLoadingHandler={this.toggleLoading}
                    />
                )
            },
            usn: {
                name: "USN",
                component: (
                    <USN
                        rows={this.state.rows}
                        serverId={this.props.serverId}
                        savePluginHandler={this.savePlugin}
                        pluginListHandler={this.pluginList}
                        addNotification={this.addNotification}
                        toggleLoadingHandler={this.toggleLoading}
                    />
                )
            }
        };
        return (
            <div className="container-fluid">
                <NotificationController
                    notifications={this.state.notifications}
                    removeNotificationAction={this.removeNotification}
                />
                <Row className="clearfix">
                    <Col sm={1}>
                        <h2>Plugins</h2>
                    </Col>
                    <Col sm={10}>
                        <Spinner
                            className="ds-float-left ds-plugin-spinner"
                            loading={this.state.loading}
                            size="md"
                        />
                    </Col>
                </Row>
                <hr />
                <Tab.Container
                    id="left-tabs-example"
                    defaultActiveKey={Object.keys(selectPlugins)[0]}
                >
                    <Row className="clearfix">
                        <Col sm={2}>
                            <Nav bsStyle="pills" stacked>
                                {Object.entries(selectPlugins).map(([id, item]) => (
                                    <NavItem key={id} eventKey={id}>
                                        {item.name}
                                    </NavItem>
                                ))}
                            </Nav>
                        </Col>
                        <Col sm={10}>
                            <Tab.Content animation={false}>
                                {Object.entries(selectPlugins).map(([id, item]) => (
                                    <Tab.Pane key={id} eventKey={id}>
                                        {item.component}
                                    </Tab.Pane>
                                ))}
                            </Tab.Content>
                        </Col>
                    </Row>
                </Tab.Container>
                <PluginEditModal
                    handleChange={this.handleFieldChange}
                    handleSwitchChange={this.handleSwitchChange}
                    pluginData={{
                        currentPluginName: this.state.currentPluginName,
                        currentPluginType: this.state.currentPluginType,
                        currentPluginEnabled: this.state.currentPluginEnabled,
                        currentPluginPath: this.state.currentPluginPath,
                        currentPluginInitfunc: this.state.currentPluginInitfunc,
                        currentPluginId: this.state.currentPluginId,
                        currentPluginVendor: this.state.currentPluginVendor,
                        currentPluginVersion: this.state.currentPluginVersion,
                        currentPluginDescription: this.state.currentPluginDescription,
                        currentPluginDependsOnType: this.state.currentPluginDependsOnType,
                        currentPluginDependsOnNamed: this.state.currentPluginDependsOnNamed,
                        currentPluginPrecedence: this.state.currentPluginPrecedence
                    }}
                    closeHandler={this.closePluginModal}
                    showModal={this.state.showPluginModal}
                    savePluginHandler={this.savePlugin}
                />
            </div>
        );
    }
}

Plugins.propTypes = {
    serverId: PropTypes.string
};

Plugins.defaultProps = {
    serverId: ""
};
