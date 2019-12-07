import React from 'react';

import styles from './CodeBlock.less';

export default function CodeBlock({color, children}) {
  return (
    <div className={styles['code-block']}>
      <pre>
        <code style={{color}}>{children}</code>
      </pre>
    </div>
  );
}
