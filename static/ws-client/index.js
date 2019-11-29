import * as $ from 'jquery';
import WSClient from "./client";

$(document).ready(() => {
  window.wsClient = new WSClient();
});
