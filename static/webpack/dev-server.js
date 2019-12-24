const webpack = require('webpack');
const DevServer = require('webpack-dev-server');
const config = require('./config/dev-with-webpack-dev-server');

new DevServer(webpack(config), {
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
});
