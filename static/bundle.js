/******/ (function(modules) { // webpackBootstrap
/******/ 	// The module cache
/******/ 	var installedModules = {};
/******/
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/
/******/ 		// Check if module is in cache
/******/ 		if(installedModules[moduleId])
/******/ 			return installedModules[moduleId].exports;
/******/
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = installedModules[moduleId] = {
/******/ 			exports: {},
/******/ 			id: moduleId,
/******/ 			loaded: false
/******/ 		};
/******/
/******/ 		// Execute the module function
/******/ 		modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/
/******/ 		// Flag the module as loaded
/******/ 		module.loaded = true;
/******/
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/
/******/
/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = modules;
/******/
/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = installedModules;
/******/
/******/ 	// __webpack_public_path__
/******/ 	__webpack_require__.p = "";
/******/
/******/ 	// Load entry module and return exports
/******/ 	return __webpack_require__(0);
/******/ })
/************************************************************************/
/******/ ([
/* 0 */
/*!*********************!*\
  !*** ./app/app.jsx ***!
  \*********************/
/***/ function(module, exports) {

	'use strict';
	
	// var FirstComponent = React.createClass({
	//     render: function() {
	//         return (
	//           <div>
	//             <h1>HELLO</h1>
	//           </div>
	//         );
	//     }
	// });
	// React.render(<FirstComponent />, document.getElementById('mount-point') );
	// import React from 'react';
	// import {render} from 'react-dom';
	//
	// class App extends React.Component {
	//   render () {
	//     return (
	//       <div>
	//         <p>Hello React!</p>
	//       </div>
	//     )
	//   }
	// }
	//
	// render(<App/>, document.getElementById('app'));
	
	console.log('HELLO');

/***/ }
/******/ ]);
//# sourceMappingURL=bundle.js.map