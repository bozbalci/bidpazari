import React from 'react';
import ReactDOM from 'react-dom';

export default function renderReact(container, className, Component, props = {}) {
  const matches = Array.from(container.querySelectorAll(className));

  if (container.classList.contains(className.replace(/^./, ''))) {
    matches.unshift(container);
  }

  if (!matches.length) return;

  matches.forEach(el => {
    const component = React.createElement(Component, props);
    ReactDOM.render(component, el);
  });
}
