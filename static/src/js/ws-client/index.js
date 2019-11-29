import * as $ from "jquery";

const socket = new WebSocket("ws://localhost:8765");

socket.onopen = event => {
  const cmd = {
    command: "login",
    params: {
      username: "bozbalci",
      password: "bozbozboz"
    }
  };

  socket.send(JSON.stringify(cmd));
};
