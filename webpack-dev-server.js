const webpack = require('webpack');
const WebpackDevServer = require('webpack-dev-server');
const config = require('./webpack.config');

new WebpackDevServer(webpack(config), {
  publicPath: config.output.publicPath,
  hot: true,
  inline: true,
  historyApiFallback: true,
  port: 3000,
  headers: {
    'Access-Control-Allow-Origin': '*',
  },
}).listen(3000, '0.0.0.0', (err, result) => {
  if (err) console.log(err);

  console.log('webpack-dev-server listening at 0.0.0.0:3000');
});
