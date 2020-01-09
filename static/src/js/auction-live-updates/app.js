import React from 'react';
import PropTypes from 'prop-types';
import {observable, runInAction} from 'mobx';
import {observer} from 'mobx-react';

import renderReact from 'utils/render-react';
import Client from 'utils/bp-client';
import bpMe from 'utils/bp-me';

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
        <p>{this.watching ? 'Live' : 'Not live'}</p>
        <p>
          {this.feed.map((item, index) => (
            <span key={index}>{JSON.stringify(item)}</span>
          ))}
        </p>
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
