#!/usr/bin/env node
import 'source-map-support/register';
import { App } from 'aws-cdk-lib';
import { FantasyBasketballSiteStack } from '../lib/fantasy-basketball-site-stack';

const app = new App();

new FantasyBasketballSiteStack(app, 'FantasyBasketballSiteStack', {
  env: { account: '959192663517', region: 'us-west-2' },
  description:
    'fantasybasketball.desdaytondigital.com - Amplify static site and read-only fantasy API',
});
