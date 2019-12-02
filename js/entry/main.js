import React from 'react';

Array.from(document.querySelectorAll('.app-loader')).forEach(appContainer => {
  const appId = appContainer.dataset.appId,
    appPropsString = appContainer.dataset.appProps,
    appProps = appPropsString ? JSON.parse(appPropsString) : {};

  // TODO Eliminate relative import here (..)

  import(/* webpackChunkName: "[request]" */ `../${appId}/app`).then(appModule => {
    appModule.default(appContainer, appProps);
  });
});
