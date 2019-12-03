import {action, observable, runInAction} from 'mobx';
import autobind from 'autobind-decorator';

export default class WSClientStore {
  @observable connected = false;
  @observable feed = [];

  constructor() {
    // Set up the WebSocket
    this.socket = new WebSocket('ws://localhost:8765');
    this.socket.onopen = this.onOpen;
    this.socket.onclose = this.onClose;
    this.socket.onmessage = this.onMessage;
  }

  @autobind
  @action
  onOpen() {
    this.connected = true;
  }

  @autobind
  @action
  onClose() {
    this.connected = false;
  }

  _sendCommand(command, params) {
    const cmdData = JSON.stringify({
      command,
      params,
    });

    this.socket.send(cmdData);
  }

  @autobind
  onMessage(event) {
    const formattedData = event.data;
    const data = JSON.parse(formattedData);

    let color;
    switch (data.code) {
      case 0:
        color = 'darkgreen';
        break;
      case 1:
        color = 'darkorange';
        break;
      case 2:
        color = 'red';
        break;
      default:
        color = 'black';
        break;
    }

    runInAction(() => {
      this.feed.push({
        data: formattedData,
        color,
      });
    });
  }

  createUser(username, password, email, first_name, last_name) {
    this._sendCommand('create_user', {
      username,
      password,
      email,
      first_name,
      last_name,
    });
  }

  login(username, password) {
    this._sendCommand('login', {
      username,
      password,
    });
  }

  changePassword(new_password, old_password) {
    this._sendCommand('change_password', {
      new_password,
      old_password,
    });
  }

  resetPassword(email) {
    this._sendCommand('reset_password', {
      email,
    });
  }

  verify(verification_number) {
    this._sendCommand('verify', {
      verification_number,
    });
  }

  logout() {
    this._sendCommand('logout', {});
  }

  addBalance(amount) {
    this._sendCommand('add_balance', {
      amount,
    });
  }

  listItems() {
    this._sendCommand('list_items', {});
  }

  viewTransactionHistory() {
    this._sendCommand('view_transaction_history', {});
  }

  createAuction(item_id, bidding_strategy_identifier, additionalParams) {
    this._sendCommand('create_auction', {
      item_id,
      bidding_strategy_identifier,
      ...additionalParams,
    });
  }

  startAuction(auction_id) {
    this._sendCommand('start_auction', {
      auction_id,
    });
  }

  bid(auction_id, amount) {
    this._sendCommand('bid', {
      auction_id,
      amount,
    });
  }

  sell(auction_id) {
    this._sendCommand('sell', {
      auction_id,
    });
  }

  viewAuctionReport(auction_id) {
    this._sendCommand('view_auction_report', {
      auction_id,
    });
  }

  viewAuctionHistory(auction_id) {
    this._sendCommand('view_auction_history', {
      auction_id,
    });
  }

  @action
  clearFeed() {
    this.feed = [];
  }
}
