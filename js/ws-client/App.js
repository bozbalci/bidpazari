import React, { Fragment } from "react";
import { observer } from "mobx-react";

import WSClientStore from "./WSClientStore";

@observer
export default class App extends React.Component {
  constructor(props) {
    super(props);

    this.store = new WSClientStore();
    window.wsClient = this.store;
  }

  render() {
    return (
      <>
        <b>
          <pre>Bidpazari WebSocket Client</pre>
        </b>
        <pre>Make queries using `wsClient` in the developer console.</pre>
        {this.store.connected ? (
          <pre>Connected to the Pazar.</pre>
        ) : (
          <pre>Connecting to the Pazar...</pre>
        )}
        <hr />
        {this.store.feed.map((item, index) => (
          <Fragment key={index}>
            <pre
              style={{
                color: item.color
              }}
            >
              {item.data}
            </pre>
            <hr />
          </Fragment>
        ))}
      </>
    );
  }
}
