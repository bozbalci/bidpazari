import React, {Fragment} from 'react';
import {observer} from 'mobx-react';

import Alert from 'react-bootstrap/Alert';
import Container from 'react-bootstrap/Container';

import renderReact from '../utils/render-react';
import WSClientStore from './WSClientStore';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';

@observer
class WSClient extends React.Component {
  constructor(props) {
    super(props);

    this.store = new WSClientStore();
    window.wsClient = this.store;

    const warningTitleCSS =
      'color:red; font-size:36px; font-weight: bold; -webkit-text-stroke: 1px black;';
    const warningDescCSS = 'font-size: 14px;';

    setTimeout(() => {
      console.log('%cBidpazari WebSocket Client', warningTitleCSS);
      console.log(
        `%cAvailable commands:

User Management     Items and Transactions     Auctions              UI
===============     ======================     ========              ==
createUser          addBalance                 createAuction         clearCommandResults
login               listItems                  startAuction          clearFeed
changePassword      viewTransactionHistory     bid
resetPassword                                  sell
verify                                         watchAuction
logout                                         viewAuctionReport
                                               viewAuctionHistory`,
        warningDescCSS,
      );
    }, 250);
  }

  render() {
    return (
      <Container fluid>
        <Row>
          <Col>
            <h1>Bidpazari WebSocket Client</h1>
            <p>
              Make queries using <code>wsClient</code> in the developer console.
            </p>
            {this.store.connected ? (
              <Alert variant="success">Connected to the Pazar.</Alert>
            ) : (
              <Alert variant="info">Connecting to the Pazar...</Alert>
            )}
            {this.store.loggedIn ? (
              <Alert variant="success">You have successfully logged in.</Alert>
            ) : (
              <Alert variant="warning">You are not currently logged in.</Alert>
            )}
          </Col>
        </Row>
        <Row>
          <Col>
            <h2>Commands</h2>
            {this.store.commandResults.map((item, index) => (
              <Fragment key={index}>
                <pre style={{color: item.color, whiteSpace: 'pre-wrap'}}>{item.data}</pre>
                <hr />
              </Fragment>
            ))}
          </Col>
          <Col>
            <h2>Notifications</h2>
            {this.store.feed.map((item, index) => (
              <Fragment key={index}>
                <pre style={{color: item.color, whiteSpace: 'pre-wrap'}}>{item.data}</pre>
                <hr />
              </Fragment>
            ))}
          </Col>
        </Row>
      </Container>
    );
  }
}

export default function bootstrap(container, props) {
  renderReact(container, '.app-ws-client', WSClient, props);
}
