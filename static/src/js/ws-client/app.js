import React from 'react';
import {observer} from 'mobx-react';

import Alert from 'react-bootstrap/Alert';
import Button from 'react-bootstrap/Button';
import ButtonGroup from 'react-bootstrap/ButtonGroup';
import Col from 'react-bootstrap/Col';
import Container from 'react-bootstrap/Container';
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

    setTimeout(() => {
      this.store.help();
    }, 250);
  }

  render() {
    return (
      <>
        <Container fluid>
          <Row className="mt-3">
            <Col sm={6}>
              <p className="my-1">
                Make queries using <code>wsClient</code> in the developer console.
              </p>
            </Col>
            <Col sm={6} className="text-right">
              <ButtonGroup>
                <Button
                  onClick={this.store.clearCommandResults}
                  variant="secondary"
                  disabled={this.store.commandResults.length === 0}
                >
                  Clear commands
                </Button>
                <Button
                  onClick={this.store.clearFeed}
                  variant="secondary"
                  disabled={this.store.feed.length === 0}
                >
                  Clear notifications
                </Button>
              </ButtonGroup>
            </Col>
          </Row>
          <Row className="mt-3">
            <Col>
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
          <Row className="mt-2">
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
