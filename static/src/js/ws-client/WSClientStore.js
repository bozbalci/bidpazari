import {action, observable, runInAction} from 'mobx';
import autobind from 'autobind-decorator';

const colors = {
  critical: '#dc3545',
  success: '#28a745',
  warning: '#ffc107',
  default: '#6c757d',
};

export default class WSClientStore {
  @observable connected = false;
  @observable loggedIn = false;

  @observable commandResults = [];
  @observable feed = [];

  help() {
    const warningTitleCSS =
      'color: red; font-size: 36px; font-weight: bold; -webkit-text-stroke: 1px black;';
    const warningDescCSS = 'font-size: 14px;';

    console.log('%cBidpazari WebSocket Client', warningTitleCSS);
    console.log(
      `%cUse wsClient to run the following commands. Use \`help\` command to view this.

User Management     Items and Transactions     Auctions              UI
===============     ======================     ========              ==
createUser          addBalance                 createAuction         clearCommandResults
login               listItems                  startAuction          clearFeed
changePassword      viewTransactionHistory     bid                   help
resetPassword                                  sell
verify                                         watchAuction
logout                                         viewAuctionReport
                                               viewAuctionHistory`,
      warningDescCSS,
    );
  }

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

    switch (data.event) {
      case 'login':
        this.onLogin(data);
        break;
      case 'logout':
        this.onLogout(data);
        break;
      case 'notification':
        this.onNotification(formattedData, data);
        return;
    }

    let color;
    switch (data.code) {
      case 0:
        color = colors.success;
        break;
      case 1:
        color = colors.warning;
        break;
      case 2:
        color = colors.critical;
        break;
      default:
        color = colors.default;
        break;
    }

    runInAction(() => {
      this.commandResults.unshift({
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

  listItems(item_type, on_sale) {
    this._sendCommand('list_items', {
      item_type,
      on_sale,
    });
  }

  watchItems(item_type) {
    this._sendCommand('watch_items', {
      item_type,
    });
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

  watchAuction(auction_id) {
    this._sendCommand('watch_auction', {
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

  @autobind
  @action
  clearCommandResults() {
    this.commandResults = [];
  }

  @autobind
  @action
  clearFeed() {
    this.feed = [];
  }

  @action
  onLogin(data) {
    if (data.code === 0) {
      // User is successfully logged in.
      this.loggedIn = true;
    }
  }

  @action
  onLogout(data) {
    if (data.code === 0) {
      this.loggedIn = false;
    }
  }

  @action
  onNotification(formattedData, data) {
    this.feed.unshift({
      formattedData,
      data,
    });
  }
}
