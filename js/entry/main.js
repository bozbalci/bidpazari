import React from "react";
import ReactDOM from "react-dom";

Array.from(document.querySelectorAll(".app")).forEach(appContainer => {
  const appName = appContainer.dataset.app;

  console.log(`Loading app: ${appName}`);

  import(/* webpackChunkName: "[request]" */ `../${appName}/app`).then(
    appModule => {
      const AppComponent = appModule.default;
      const appComponent = <AppComponent />;
      ReactDOM.render(appComponent, appContainer);
    }
  );
});
