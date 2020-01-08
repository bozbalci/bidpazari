import React from 'react';

// Load jQuery and Popper.js
import 'bootstrap/dist/js/bootstrap.min';

import $ from 'jquery';

import 'main.global.scss';

// Mount React components
Array.from(document.querySelectorAll('.app-loader')).forEach(appContainer => {
  const appId = appContainer.dataset.appId,
    appPropsString = appContainer.dataset.appProps,
    appProps = appPropsString ? JSON.parse(appPropsString) : {};

  // TODO Eliminate relative import here (..)

  import(/* webpackChunkName: "[request]" */ `../${appId}/app`).then(appModule => {
    appModule.default(appContainer, appProps);
  });
});

// Enable Bootstrap tooltips for Django templates
$('[data-toggle="tooltip"]').tooltip();
