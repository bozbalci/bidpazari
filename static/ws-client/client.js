export default class WSClient {
  constructor() {
    this.socket = new WebSocket("ws://localhost:8765");
    this.socket.onmessage = this._onMessage.bind(this);
  }

  _sendCommand(command, params) {
    const cmdData = JSON.stringify({
      command,
      params,
    });

    this.socket.send(cmdData);
  }

  _onMessage(event) {
    const data = event.data;
    console.log(data);
  }

  createUser(username, password, email, first_name, last_name) {
    this._sendCommand(
      "create_user",
      {
        username, password, email, first_name, last_name
      });
  }

  login(username, password) {
    this._sendCommand(
      "login",
      {
        username, password
      });
  }

  addBalance(amount) {
    this._sendCommand(
      "add_balance",
      {
        amount
      });
  }
}
