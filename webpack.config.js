var webpack = require('webpack');
var path = require('path');

var BUILD_DIR = path.resolve(__dirname, 'static');
var APP_DIR = path.resolve(__dirname, 'app');

var config = {
  entry: APP_DIR + '/app.jsx',
  output: {
    path: BUILD_DIR,
    filename: 'bundle.js'
  },
  module : {
    loaders : [
      {
        test : /\.jsx?/,
        include : APP_DIR,
        exclude: /node_modules/,
        loader : 'babel',
        query:
        {
          presets: ["es2015", "react"]
        }
      }
    ]
  }
};

module.exports = config;
