import React, {Fragment} from 'react';
import {observer} from 'mobx-react';

import Alert from 'react-bootstrap/Alert';
import Button from 'react-bootstrap/Button';
import Col from 'react-bootstrap/Col';
import Container from 'react-bootstrap/Container';
import Form from 'react-bootstrap/Form';
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import Row from 'react-bootstrap/Row';

import renderReact from '../utils/render-react';
import WSClientStore from './WSClientStore';
import CodeBlock from './CodeBlock';

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
        `%cUse wsClient to run the following commands:

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
      <>
        <Navbar bg="success" variant="dark">
          <Navbar.Brand>Bidpazari WebSocket Client</Navbar.Brand>
          <Nav className="mr-auto"></Nav>
          <Form inline>
            {this.store.commandResults.length > 0 ? (
              <Button
                onClick={this.store.clearCommandResults}
                variant="outline-light"
                className="mx-1"
              >
                Clear commands
              </Button>
            ) : null}
            {this.store.feed.length > 0 ? (
              <Button onClick={this.store.clearFeed} variant="outline-light" className="mx-1">
                Clear notifications
              </Button>
            ) : null}
          </Form>
        </Navbar>
        <Container fluid>
          <Row className="mt-3">
            <Col>
              <p>
                Make queries using <code>wsClient</code> in the developer console.
              </p>
              {this.store.connected ? (
                this.store.loggedIn ? (
                  <Alert variant="success">You have successfully logged into the Pazar.</Alert>
                ) : (
                  <Alert variant="warning">
                    Connected to the Pazar, but you are not logged in. Use the <code>login</code>{' '}
                    command.
                  </Alert>
                )
              ) : (
                <Alert variant="info">Connecting to the Pazar...</Alert>
              )}
            </Col>
          </Row>
          <Row>
            <Col style={{borderRight: '1px solid #DDD'}}>
              <h2 className="text-center">Commands</h2>
              {this.store.commandResults.map((item, index) => (
                <CodeBlock color={item.color} key={index}>
                  {item.data}
                </CodeBlock>
              ))}
            </Col>
            <Col>
              <h2 className="text-center">Notifications</h2>
              {this.store.feed.map((item, index) => (
                <CodeBlock color={'#FFF'} key={index}>
                  {item.formattedData}
                </CodeBlock>
              ))}
            </Col>
          </Row>
        </Container>
      </>
    );
  }
}

export default function bootstrap(container, props) {
  renderReact(container, '.app-ws-client', WSClient, props);
}
