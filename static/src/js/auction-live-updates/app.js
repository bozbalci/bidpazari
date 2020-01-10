import React from 'react';
import ReactDOM from 'react-dom';
import PropTypes from 'prop-types';
import {observable, runInAction} from 'mobx';
import {observer} from 'mobx-react';
import Badge from 'react-bootstrap/Badge';
import moment from 'moment';

import renderReact from 'utils/render-react';
import Client from 'utils/bp-client';
import bpMe from 'utils/bp-me';

const liveUpdatesRoot = document.querySelector('#auction-live-updates-tbody');
const liveUpdatesStatusRoot = document.querySelector('#auction-live-updates-status');

class AuctionLiveUpdatesStatus extends React.Component {
  constructor(props) {
    super(props);

    liveUpdatesStatusRoot.innerHTML = '';
  }

  render() {
    return ReactDOM.createPortal(<Badge variant="success">Live</Badge>, liveUpdatesStatusRoot);
  }
}

class AuctionLiveUpdatesRow extends React.Component {
  constructor(props) {
    super(props);

    this.trElement = document.createElement('tr');
  }

  componentDidMount() {
    liveUpdatesRoot.prepend(this.trElement);
  }

  componentWillUnmount() {
    liveUpdatesRoot.removeChild(this.trElement);
  }

  render() {
    const formattedTimestamp = moment(this.props.timestamp)
      .utc()
      .format('MMM. D, Y - HH:mm:ss');

    return ReactDOM.createPortal(
      <>
        <td>{formattedTimestamp}</td>
        <td>{this.props.message}</td>
      </>,
      this.trElement,
    );
  }

  static propTypes = {
    timestamp: PropTypes.string.isRequired,
    message: PropTypes.string.isRequired,
  };
}

@observer
class AuctionLiveUpdates extends React.Component {
  @observable connected = false;
  @observable loggedIn = false;
  @observable watching = false;
  @observable feed = [];

  constructor(props) {
    super(props);

    this.client = new Client();
    window.client = this.client;

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

      this.client.watchAuction(this.props.auctionId);
    };

    this.client.on.logout = data => {
      runInAction(() => {
        this.loggedIn = false;
      });
    };

    this.client.on.watch_auction = data => {
      runInAction(() => {
        this.watching = true;
      });
    };

    this.client.on.notification_auction = data => {
      this.feed.unshift(data);
    };
  }

  componentDidMount() {
    this.client.connect();
  }

  render() {
    return (
      <>
        <AuctionLiveUpdatesStatus />
        {this.feed
          .slice(0)
          .reverse()
          .map((item, index) => (
            <AuctionLiveUpdatesRow
              key={index}
              timestamp={item.timestamp}
              message={item.result.msg}
            />
          ))}
      </>
    );
  }

  static propTypes = {
    auctionId: PropTypes.number.isRequired,
  };
}

export default function bootstrap(container, props) {
  renderReact(container, '.app-auction-live-updates', AuctionLiveUpdates, props);
}
