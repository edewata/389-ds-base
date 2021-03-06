import React from "react";
import {
    Modal,
    Row,
    Col,
    ControlLabel,
    Icon,
    Button,
    Form,
    FormControl,
    Spinner,
    noop
} from "patternfly-react";
import { LDIFTable } from "./databaseTables.jsx";
import PropTypes from "prop-types";
import "../../css/ds.css";

class CreateLinkModal extends React.Component {
    render() {
        const {
            showModal,
            closeHandler,
            handleChange,
            saveHandler,
            suffix,
            pwdMatch,
            error,
        } = this.props;

        return (
            <Modal show={showModal} onHide={closeHandler}>
                <div className="ds-no-horizontal-scrollbar">
                    <Modal.Header>
                        <button
                            className="close"
                            onClick={closeHandler}
                            aria-hidden="true"
                            aria-label="Close"
                        >
                            <Icon type="pf" name="close" />
                        </button>
                        <Modal.Title>
                            Create Database Link
                        </Modal.Title>
                    </Modal.Header>
                    <Modal.Body>
                        <Form horizontal autoComplete="off">
                            <div>
                                <label htmlFor="createLinkSuffix" className="ds-config-label" title="The RDN of the link suffix">
                                    Link Sub-Suffix</label><input className={error.createLinkSuffix ? "ds-input-bad ds-input-right" : "ds-input ds-input-right"} onChange={handleChange} type="text" id="createLinkSuffix" size="12" /><b><font color="blue"> ,{suffix}</font></b>
                            </div>
                            <div>
                                <label htmlFor="createLinkName" className="ds-config-label" title="A name for the backend chaining database link">
                                    Link Database Name</label><input onChange={handleChange} className={error.createLinkName ? "ds-input-bad" : "ds-input"} type="text" id="createLinkName" size="45" />
                            </div>
                            <div>
                                <label htmlFor="createNsfarmserverurl" className="ds-config-label" title="The LDAP URL for the remote server.  Add additional failover LDAP URLs separated by a space. (nsfarmserverurl)">
                                    Remote Server URL(s)</label><input className={error.createNsfarmserverurl ? "ds-input-bad" : "ds-input"} onChange={handleChange} type="text" id="createNsfarmserverurl" size="45" />
                            </div>
                            <div>
                                <input type="checkbox" onChange={handleChange} className="ds-left-indent ds-config-checkbox" id="createUseStartTLS" /><label
                                    htmlFor="createUseStartTLS" className="ds-label" title="Use StartTLS for the remote server LDAP URL"> Use StartTLS</label>
                            </div>
                            <div>
                                <label htmlFor="createNsmultiplexorbinddn" className="ds-config-label" title="Bind DN used to authenticate against the remote server (nsmultiplexorbinddn).">Remote Server Bind DN</label><input
                                    className={error.createNsmultiplexorbinddn ? "ds-input-bad" : "ds-input"} type="text" onChange={handleChange} placeholder="Bind DN" id="createNsmultiplexorbinddn" size="45" />
                            </div>
                            <div>
                                <label htmlFor="createNsmultiplexorcredentials" className="ds-config-label" title="Replication Bind DN (nsDS5ReplicaCredentials).">Bind DN Credentials</label><input
                                    className={error.createNsmultiplexorcredentials ? "ds-input-bad" : "ds-input"} type="password" onChange={handleChange} placeholder="Enter password" id="createNsmultiplexorcredentials" size="45" />
                            </div>
                            <div>
                                <label htmlFor="createNsmultiplexorcredentialsConfirm" className="ds-config-label" title="Confirm password">Confirm Password</label><input
                                    className={(error.createNsmultiplexorcredentialsConfirm || !pwdMatch) ? "ds-input-bad" : "ds-input"} type="password" onChange={handleChange} placeholder="Confirm password" id="createNsmultiplexorcredentialsConfirm" size="45" />
                            </div>
                            <div>
                                <label htmlFor="createNsbindmechanism" className="ds-config-label" title="The bind method for contacting the remote server  (nsbindmechanism).">Bind Method</label><select
                                    className="btn btn-default dropdown ds-dblink-dropdown" onChange={handleChange} id="createNsbindmechanism">
                                    <option>Simple</option>
                                    <option>SASL/DIGEST-MD5</option>
                                    <option>SASL/GSSAPI</option>
                                </select>
                            </div>
                        </Form>
                    </Modal.Body>
                    <Modal.Footer>
                        <Button
                            bsStyle="default"
                            className="btn-cancel"
                            onClick={closeHandler}
                        >
                            Cancel
                        </Button>
                        <Button
                            bsStyle="primary"
                            onClick={saveHandler}
                        >
                            Create Database Link
                        </Button>
                    </Modal.Footer>
                </div>
            </Modal>
        );
    }
}

class CreateSubSuffixModal extends React.Component {
    render() {
        const {
            showModal,
            closeHandler,
            handleChange,
            saveHandler,
            suffix,
            error
        } = this.props;

        return (
            <Modal show={showModal} onHide={closeHandler}>
                <div>
                    <Modal.Header>
                        <button
                            className="close"
                            onClick={closeHandler}
                            aria-hidden="true"
                            aria-label="Close"
                        >
                            <Icon type="pf" name="close" />
                        </button>
                        <Modal.Title>
                            Create Sub Suffix
                        </Modal.Title>
                    </Modal.Header>
                    <Modal.Body>
                        <Form horizontal autoComplete="off">
                            <Row title="Database Suffix DN (nsslapd-suffix)">
                                <Col sm={3}>
                                    <ControlLabel>Sub-Suffix DN</ControlLabel>
                                </Col>
                                <Col sm={3}>
                                    <FormControl
                                        type="text"
                                        id="subSuffixValue"
                                        className={error.subSuffixValue ? "ds-input-bad ds-input-right" : "ds-input-right"}
                                        onChange={handleChange}
                                    />
                                </Col>
                                <Col sm={6} className="ds-col-append">
                                    <ControlLabel><b><font color="blue">,{suffix}</font></b></ControlLabel>
                                </Col>
                            </Row>
                            <p />
                            <Row title="Database backend name (nsslapd-backend)">
                                <Col sm={3}>
                                    <ControlLabel>Backend Name</ControlLabel>
                                </Col>
                                <Col sm={9}>
                                    <FormControl
                                        type="text"
                                        id="subSuffixBeName"
                                        className={error.subSuffixBeName ? "ds-input-bad" : ""}
                                        onChange={handleChange}
                                    />
                                </Col>
                            </Row>
                        </Form>
                    </Modal.Body>
                    <Modal.Footer>
                        <Button
                            bsStyle="default"
                            className="btn-cancel"
                            onClick={closeHandler}
                        >
                            Cancel
                        </Button>
                        <Button
                            bsStyle="primary"
                            onClick={saveHandler}
                        >
                            Create Sub-Suffix
                        </Button>
                    </Modal.Footer>
                </div>
            </Modal>
        );
    }
}

class ExportModal extends React.Component {
    render() {
        const {
            showModal,
            closeHandler,
            handleChange,
            saveHandler,
            spinning,
            error
        } = this.props;
        let spinner = "";
        if (spinning) {
            spinner =
                <Row>
                    <div className="ds-modal-spinner">
                        <Spinner loading inline size="lg" />Exporting database... <font size="1">(You can safely close this window)</font>
                    </div>
                </Row>;
        }

        return (
            <Modal show={showModal} onHide={closeHandler}>
                <div className="ds-no-horizontal-scrollbar">
                    <Modal.Header>
                        <button
                            className="close"
                            onClick={closeHandler}
                            aria-hidden="true"
                            aria-label="Close"
                        >
                            <Icon type="pf" name="close" />
                        </button>
                        <Modal.Title>
                            Export Database To LDIF File
                        </Modal.Title>
                    </Modal.Header>
                    <Modal.Body>
                        <Form horizontal autoComplete="off">
                            <Row title="Name of exported LDIF file">
                                <Col sm={3}>
                                    <ControlLabel>LDIF File Name</ControlLabel>
                                </Col>
                                <Col sm={9}>
                                    <FormControl
                                        type="text"
                                        id="ldifLocation"
                                        className={error.ldifLocation ? "ds-input-bad" : ""}
                                        onChange={handleChange}
                                    />
                                </Col>
                            </Row>
                            <p />
                            {spinner}
                        </Form>
                    </Modal.Body>
                    <Modal.Footer>
                        <Button
                            bsStyle="default"
                            className="btn-cancel"
                            onClick={closeHandler}
                        >
                            Cancel
                        </Button>
                        <Button
                            bsStyle="primary"
                            onClick={saveHandler}
                        >
                            Export Database
                        </Button>
                    </Modal.Footer>
                </div>
            </Modal>
        );
    }
}

class ImportModal extends React.Component {
    render() {
        const {
            showModal,
            closeHandler,
            handleChange,
            saveHandler,
            spinning,
            rows,
            suffix
        } = this.props;

        let suffixRows = [];
        let spinner = "";
        if (spinning) {
            spinner =
                <Row>
                    <div className="ds-modal-spinner">
                        <p />
                        <Spinner loading inline size="lg" />Importing LDIF file... <font size="1">(You can safely close this window)</font>
                    </div>
                </Row>;
        }
        for (let idx in rows) {
            if (rows[idx].suffix == suffix) {
                suffixRows.push(rows[idx]);
            }
        }

        return (
            <Modal show={showModal} onHide={closeHandler}>
                <div className="ds-no-horizontal-scrollbar">
                    <Modal.Header>
                        <button
                            className="close"
                            onClick={closeHandler}
                            aria-hidden="true"
                            aria-label="Close"
                        >
                            <Icon type="pf" name="close" />
                        </button>
                        <Modal.Title>
                            Initialize Database via LDIF File
                        </Modal.Title>
                    </Modal.Header>
                    <Modal.Body>
                        <p />
                        <LDIFTable
                            rows={suffixRows}
                            confirmImport={this.props.showConfirmImport}
                        />
                        <hr />
                        <Form horizontal autoComplete="off">
                            <Row title="The full path to the LDIF file.  The server must have permissions to read it">
                                <Col sm={4}>
                                    <ControlLabel>Or, enter LDIF location</ControlLabel>
                                </Col>
                                <Col sm={6}>
                                    <FormControl
                                        type="text"
                                        id="ldifLocation"
                                        onChange={handleChange}
                                    />
                                </Col>
                                <Col sm={2}>
                                    <Button
                                        bsStyle="primary"
                                        onClick={saveHandler}
                                    >
                                        Import
                                    </Button>
                                </Col>
                            </Row>
                            <p />
                            {spinner}
                        </Form>
                    </Modal.Body>
                    <Modal.Footer>
                        <Button
                            bsStyle="default"
                            className="btn-cancel"
                            onClick={closeHandler}
                        >
                            Close
                        </Button>
                    </Modal.Footer>
                </div>
            </Modal>
        );
    }
}

class ReindexModal extends React.Component {
    render() {
        const {
            showModal,
            closeHandler,
            msg
        } = this.props;

        return (
            <Modal show={showModal} onHide={closeHandler}>
                <div className="ds-no-horizontal-scrollbar">
                    <Modal.Header>
                        <button
                            className="close"
                            onClick={closeHandler}
                            aria-hidden="true"
                            aria-label="Close"
                        >
                            <Icon type="pf" name="close" />
                        </button>
                        <Modal.Title>
                            Index Attribute
                        </Modal.Title>
                    </Modal.Header>
                    <Modal.Body>
                        <Form horizontal autoComplete="off">
                            <div className="ds-modal-spinner">
                                <Spinner loading inline size="lg" /> Indexing <b>{msg}</b> ...
                                <p><font size="1">(You can safely close this window)</font></p>
                            </div>
                        </Form>
                    </Modal.Body>
                    <Modal.Footer>
                        <Button
                            bsStyle="default"
                            className="btn-cancel"
                            onClick={closeHandler}
                        >
                            Close
                        </Button>
                    </Modal.Footer>
                </div>
            </Modal>
        );
    }
}

// Property types and defaults

CreateLinkModal.propTypes = {
    showModal: PropTypes.bool,
    closeHandler: PropTypes.func,
    handleChange: PropTypes.func,
    saveHandler: PropTypes.func,
    suffix: PropTypes.string,
    pwdMatch: PropTypes.bool,
    error: PropTypes.object,
};

CreateLinkModal.defaultProps = {
    showModal: false,
    closeHandler: noop,
    handleChange: noop,
    saveHandler: noop,
    suffix: "",
    pwdMatch: false,
    error: {},
};

CreateSubSuffixModal.propTypes = {
    showModal: PropTypes.bool,
    closeHandler: PropTypes.func,
    handleChange: PropTypes.func,
    saveHandler: PropTypes.func,
    suffix: PropTypes.string,
    error: PropTypes.object,
};

CreateSubSuffixModal.defaultProps = {
    showModal: false,
    closeHandler: noop,
    handleChange: noop,
    saveHandler: noop,
    suffix: "",
    error: {},
};

ExportModal.propTypes = {
    showModal: PropTypes.bool,
    closeHandler: PropTypes.func,
    handleChange: PropTypes.func,
    saveHandler: PropTypes.func,
    error: PropTypes.object,
    spinning: PropTypes.bool
};

ExportModal.defaultProps = {
    showModal: false,
    closeHandler: noop,
    handleChange: noop,
    saveHandler: noop,
    error: {},
    spinning: false
};

ImportModal.propTypes = {
    showModal: PropTypes.bool,
    closeHandler: PropTypes.func,
    handleChange: PropTypes.func,
    saveHandler: PropTypes.func,
    spinning: PropTypes.bool,
    showConfirmImport: PropTypes.func,
    rows: PropTypes.array,
    suffix: PropTypes.string
};

ImportModal.defaultProps = {
    showModal: false,
    closeHandler: noop,
    handleChange: noop,
    saveHandler: noop,
    spinning: false,
    showConfirmImport: noop,
    rows: [],
    suffix: ""
};

ReindexModal.propTypes = {
    showModal: PropTypes.bool,
    closeHandler: PropTypes.func,
    msg: PropTypes.string
};

ReindexModal.defaultProps = {
    showModal: false,
    closeHandler: noop,
    msg: ""
};

export {
    ReindexModal,
    ImportModal,
    ExportModal,
    CreateSubSuffixModal,
    CreateLinkModal,
};
