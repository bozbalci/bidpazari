import React, {Fragment} from 'react';
import {action, computed, observable, runInAction, toJS} from 'mobx';
import autobind from 'autobind-decorator';
import {observer} from 'mobx-react';

import renderReact from 'utils/render-react';
import Client from 'utils/bp-client';
import bpMe from 'utils/bp-me';
import {Badge, FormControl, Image, InputGroup, Table} from 'react-bootstrap';

@observer
class AuctionList extends React.Component {
  render() {
    const {auctions} = this.props;

    return (
      <Table hover responsive={'sm'}>
        <thead>
          <tr>
            <th>
              <span className="sr-only">Image</span>
            </th>
            <th>Title</th>
            <th>Description</th>
            <th>Type</th>
            <th>Owner</th>
            <th>Price</th>
            <th>Bidding Strategy</th>
            <th>
              <span className="sr-only">Auction Link</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {auctions.map((item, index) => (
            <tr key={index}>
              <td>
                <Image
                  style={{
                    maxWidth: '100px',
                  }}
                  src={
                    item.item_image ? `/media/${item.item_image}` : `/staticx/images/question.jpg`
                  }
                  alt={item.item}
                  width={100}
                />
              </td>
              <td>{item.item}</td>
              <td>{item.description}</td>
              <td>{item.item_type}</td>
              <td>{item.owner}</td>
              <td>{item.current_price}</td>
              <td>{item.bidding_strategy}</td>
              <td>
                <a className="btn btn-info" href={`/auctions/${item.id}`}>
                  View
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    );
  }
}

@observer
class AuctionMonitor extends React.Component {
  constructor(props) {
    super(props);

    this.client = new Client();
    window.client = this.client; // TODO remove me

    this.client.on.open = data => {
      runInAction(() => {
        this.connected = true;
      });

      if (!this.client.loggedIn) {
        this.client.loginToken(bpMe.username, bpMe.authToken);
      }
    };

    this.client.on.close = data => {
      runInAction(() => {
        this.connected = false;
      });
    };

    this.client.on.login = data => {
      runInAction(() => {
        this.loggedIn = true;
      });
    };

    this.client.on.logout = data => {
      runInAction(() => {
        this.loggedIn = false;
      });
    };

    this.client.on.notification_item = data => {
      runInAction(() => {
        this.auctions.push(data.result.auction);
      });
    };
  }

  @observable formInput = '';
  @observable watchedItemTypes = new Set();
  @observable auctions = [];

  // WebSocket variables
  @observable connected = false;
  @observable loggedIn = false;

  @autobind
  @action
  addItem(event) {
    event.preventDefault();

    const itemType = this.formInput;

    if (!this.watchedItemTypes.has(itemType)) {
      this.watchedItemTypes.add(itemType);

      // User must already be logged in
      this.client.watchItems(itemType);
    }

    this.formInput = '';
  }

  @autobind
  @action
  handleInput(event) {
    this.formInput = event.target.value;
  }

  @computed
  get auctionsList() {
    return toJS(this.auctions);
  }

  componentDidMount() {
    this.client.connect();
  }

  render() {
    return (
      <>
        <h3>Monitor</h3>
        {this.loggedIn ? (
          <>
            <p>Type an item type and hit enter to add it to your monitored items.</p>
            <form onSubmit={this.addItem}>
              <InputGroup>
                <InputGroup.Prepend>
                  <InputGroup.Text>Type</InputGroup.Text>
                </InputGroup.Prepend>
                <FormControl
                  placeholder={'Kitchen'}
                  onChange={this.handleInput}
                  value={this.formInput}
                />
              </InputGroup>
            </form>

            <h5 className="mt-2">
              {Array.from(this.watchedItemTypes.values()).map((item, index) => (
                <Fragment key={index}>
                  <Badge variant={'secondary'} pill>
                    {item}
                  </Badge>{' '}
                </Fragment>
              ))}
            </h5>

            <hr />

            {this.auctionsList.length > 0 ? <AuctionList auctions={this.auctionsList} /> : null}
          </>
        ) : (
          <h3>Connecting...</h3>
        )}
      </>
    );
  }
}

export default function bootstrap(container, props) {
  renderReact(container, '.app-auction-monitor', AuctionMonitor, props);
}
