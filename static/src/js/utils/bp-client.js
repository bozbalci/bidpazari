import {action, observable, runInAction} from 'mobx';
import autobind from 'autobind-decorator';

export default class Client {
  @observable connected = false;
  @observable loggedIn = false;

  @observable commandResults = [];
  @observable feed = [];

  socket;

  on = {
    // Generic handlers
    open: null,
    close: null,
    // Command handlers
    login: null,
    watch_auction: null,
    // Notifications
    notification_auction: null,
  };

  handleEvent(eventType, data) {
    const handler = this.on[eventType];

    if (handler) {
      const boundHandler = handler.bind(this);
      boundHandler(data);
    }
  }

  connect() {
    this.socket = new WebSocket('ws://localhost:8765');
    this.socket.onopen = this.onOpen;
    this.socket.onclose = this.onClose;
    this.socket.onmessage = this.onMessage;
  }

  /// GENERIC HANDLERS =============================================================================

  @autobind
  @action
  onOpen() {
    this.connected = true;

    this.handleEvent('open', {});
  }

  @autobind
  @action
  onClose() {
    this.connected = false;

    this.handleEvent('close', {});
  }

  @autobind
  onMessage(event) {
    const data = JSON.parse(event.data);

    switch (data.event) {
      case 'login':
      case 'login_with_auth_token':
        this.onLogin(data);
        break;
      case 'logout':
        this.onLogout(data);
        break;
      case 'notification':
        this.onNotification(data);
        break;
      default:
        this.handleEvent(data.event, data);
        return;
    }
  }

  /// COMMANDS =====================================================================================

  _sendCommand(command, params) {
    const cmdData = JSON.stringify({
      command,
      params,
    });

    this.socket.send(cmdData);
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

  loginToken(username, auth_token) {
    this._sendCommand('login_with_auth_token', {
      username,
      auth_token,
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

  /// EVENT HANDLERS ===============================================================================

  @action
  onLogin(data) {
    if (data.code === 0) {
      // User is successfully logged in.
      this.loggedIn = true;
    }

    this.handleEvent('login', data);
  }

  @action
  onLogout(data) {
    if (data.code === 0) {
      this.loggedIn = false;
    }

    this.handleEvent('logout', data);
  }

  @action
  onNotification(data) {
    if (data.result.domain === 'auction') {
      this.handleEvent('notification_auction', data);
    }
  }
}
