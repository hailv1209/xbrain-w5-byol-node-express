// lambda.js — Express app handler for AWS Lambda
// Wraps app.js with serverless-http adapter
// This is the ONLY file added to make it work on Lambda (minimal code change strategy)

const serverlessHttp = require('serverless-http');
const app = require('./app');

module.exports.handler = serverlessHttp(app);
