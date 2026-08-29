import * as path from 'path';
import {
  CfnOutput,
  Duration,
  RemovalPolicy,
  Stack,
  StackProps,
} from 'aws-cdk-lib';
import * as amplify from 'aws-cdk-lib/aws-amplify';
import * as apigatewayv2 from 'aws-cdk-lib/aws-apigatewayv2';
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

const DOMAIN_NAME = 'desdaytondigital.com';
const SITE_DOMAIN = `fantasybasketball.${DOMAIN_NAME}`;
const BRANCH_NAME = 'master';
const GITHUB_REPOSITORY = 'moneypro/fantasy_basketball_tools';
const AMPLIFY_APP_NAME = 'fantasy-basketball';
const ESPN_SECRET_NAME = 'fantasy-basketball/espn';

export class FantasyBasketballSiteStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // ------------------------------------------------------------------
    // Static site (manual ZIP deploy - no connected repository)
    // ------------------------------------------------------------------
    const amplifyApp = new amplify.CfnApp(this, 'AmplifyApp', {
      name: AMPLIFY_APP_NAME,
      platform: 'WEB',
      enableBranchAutoDeletion: false,
      buildSpec: [
        'version: 1',
        'frontend:',
        '  phases:',
        '    build:',
        '      commands: []',
        '  artifacts:',
        '    baseDirectory: /',
        '    files:',
        "      - '**/*'",
        '  cache:',
        '    paths: []',
      ].join('\n'),
    });

    const branch = new amplify.CfnBranch(this, 'MasterBranch', {
      appId: amplifyApp.attrAppId,
      branchName: BRANCH_NAME,
      enableAutoBuild: false,
      stage: 'PRODUCTION',
    });

    // Associate the subdomain directly (the apex desdaytondigital.com is
    // already associated with the ddd-website Amplify app).
    const domainAssociation = new amplify.CfnDomain(this, 'AmplifyDomain', {
      appId: amplifyApp.attrAppId,
      domainName: SITE_DOMAIN,
      enableAutoSubDomain: false,
      subDomainSettings: [
        {
          branchName: BRANCH_NAME,
          prefix: '',
        },
      ],
    });
    domainAssociation.addDependency(branch);

    const siteOrigins = [
      `https://${SITE_DOMAIN}`,
      `https://${BRANCH_NAME}.${amplifyApp.attrDefaultDomain}`,
    ];

    // ------------------------------------------------------------------
    // ESPN credentials. The template only ever holds a placeholder; the real
    // values are pushed in by the deploy workflow from GitHub secrets.
    // ------------------------------------------------------------------
    const espnSecret = new secretsmanager.Secret(this, 'EspnSecret', {
      secretName: ESPN_SECRET_NAME,
      description:
        'ESPN fantasy basketball credentials (ESPN_S2, SWID, LEAGUE_ID). Values are written by the deploy workflow.',
      generateSecretString: {
        secretStringTemplate: JSON.stringify({
          ESPN_S2: 'REPLACE_ME',
          SWID: 'REPLACE_ME',
          LEAGUE_ID: 'REPLACE_ME',
        }),
        generateStringKey: 'placeholder',
      },
    });
    espnSecret.applyRemovalPolicy(RemovalPolicy.RETAIN);

    // ------------------------------------------------------------------
    // Read-only public API
    // ------------------------------------------------------------------
    const apiHandler = new lambda.Function(this, 'ApiHandler', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname, '..', '..', 'lambda', 'build'),
      ),
      timeout: Duration.seconds(30),
      memorySize: 512,
      logRetention: logs.RetentionDays.ONE_MONTH,
      environment: {
        ESPN_SECRET_NAME: ESPN_SECRET_NAME,
        ALLOWED_ORIGINS: siteOrigins.join(','),
      },
    });

    espnSecret.grantRead(apiHandler);

    const httpApi = new apigatewayv2.HttpApi(this, 'FantasyApi', {
      apiName: 'fantasy-basketball-api',
      description: 'Public read-only API for fantasybasketball.desdaytondigital.com',
      corsPreflight: {
        allowOrigins: siteOrigins,
        allowMethods: [
          apigatewayv2.CorsHttpMethod.GET,
          apigatewayv2.CorsHttpMethod.OPTIONS,
        ],
        allowHeaders: ['content-type'],
        maxAge: Duration.days(1),
      },
    });

    const apiIntegration = new HttpLambdaIntegration(
      'ApiHandlerIntegration',
      apiHandler,
    );

    httpApi.addRoutes({
      path: '/api/{proxy+}',
      methods: [apigatewayv2.HttpMethod.ANY],
      integration: apiIntegration,
    });

    httpApi.addRoutes({
      path: '/api',
      methods: [apigatewayv2.HttpMethod.ANY],
      integration: apiIntegration,
    });

    // This endpoint is public and unauthenticated, and every cache miss makes a
    // request to ESPN with the league's credentials. Throttle the default stage
    // so a hostile or accidental flood cannot run up Lambda cost or hammer ESPN.
    const defaultStage = httpApi.defaultStage!.node
      .defaultChild as apigatewayv2.CfnStage;
    defaultStage.defaultRouteSettings = {
      throttlingRateLimit: 20,
      throttlingBurstLimit: 40,
    };

    // ------------------------------------------------------------------
    // GitHub Actions OIDC deploy role
    // ------------------------------------------------------------------
    // The OIDC provider for token.actions.githubusercontent.com already exists
    // in this account (created by DddWebsiteStack) - import it, never create it.
    const githubActionsProvider =
      iam.OpenIdConnectProvider.fromOpenIdConnectProviderArn(
        this,
        'GitHubActionsProvider',
        `arn:aws:iam::${this.account}:oidc-provider/token.actions.githubusercontent.com`,
      );

    const githubActionsDeployRole = new iam.Role(
      this,
      'GitHubActionsDeployRole',
      {
        assumedBy: new iam.WebIdentityPrincipal(
          githubActionsProvider.openIdConnectProviderArn,
          {
            StringEquals: {
              'token.actions.githubusercontent.com:aud': 'sts.amazonaws.com',
            },
            StringLike: {
              'token.actions.githubusercontent.com:sub': `repo:${GITHUB_REPOSITORY}:ref:refs/heads/${BRANCH_NAME}`,
            },
          },
        ),
        description:
          'Allows GitHub Actions to deploy the fantasy basketball site and API.',
      },
    );

    githubActionsDeployRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['cloudformation:DescribeStacks'],
        resources: [
          `arn:aws:cloudformation:${this.region}:${this.account}:stack/${this.stackName}/*`,
        ],
      }),
    );

    githubActionsDeployRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          'amplify:CreateDeployment',
          'amplify:StartDeployment',
          'amplify:GetJob',
        ],
        resources: [
          `arn:aws:amplify:${this.region}:${this.account}:apps/${amplifyApp.attrAppId}`,
          `arn:aws:amplify:${this.region}:${this.account}:apps/${amplifyApp.attrAppId}/branches/${BRANCH_NAME}`,
          `arn:aws:amplify:${this.region}:${this.account}:apps/${amplifyApp.attrAppId}/branches/${BRANCH_NAME}/deployments/*`,
          `arn:aws:amplify:${this.region}:${this.account}:apps/${amplifyApp.attrAppId}/branches/${BRANCH_NAME}/jobs/*`,
        ],
      }),
    );

    githubActionsDeployRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          'secretsmanager:PutSecretValue',
          'secretsmanager:DescribeSecret',
        ],
        resources: [espnSecret.secretArn],
      }),
    );

    // Lets the workflow run `cdk deploy` by assuming the CDK bootstrap roles.
    githubActionsDeployRole.addToPolicy(
      new iam.PolicyStatement({
        // TagSession is included because the bootstrap roles' trust policy
        // allows it and the CDK CLI may tag the assumed session.
        actions: ['sts:AssumeRole', 'sts:TagSession'],
        resources: [
          `arn:aws:iam::*:role/cdk-hnb659fds-*-role-${this.account}-${this.region}`,
        ],
      }),
    );

    // The CDK CLI reads the bootstrap version from SSM before deploying.
    githubActionsDeployRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['ssm:GetParameter'],
        resources: [
          `arn:aws:ssm:${this.region}:${this.account}:parameter/cdk-bootstrap/hnb659fds/version`,
        ],
      }),
    );

    // ------------------------------------------------------------------
    // Outputs
    // ------------------------------------------------------------------
    new CfnOutput(this, 'AmplifyAppId', {
      value: amplifyApp.attrAppId,
    });
    new CfnOutput(this, 'AmplifyDefaultDomain', {
      value: amplifyApp.attrDefaultDomain,
    });
    new CfnOutput(this, 'AmplifyBranchName', {
      value: BRANCH_NAME,
    });
    new CfnOutput(this, 'ApiUrl', {
      value: httpApi.apiEndpoint,
    });
    new CfnOutput(this, 'WebsiteUrl', {
      value: `https://${SITE_DOMAIN}`,
    });
    new CfnOutput(this, 'GitHubActionsDeployRoleArn', {
      value: githubActionsDeployRole.roleArn,
    });
    new CfnOutput(this, 'EspnSecretName', {
      value: ESPN_SECRET_NAME,
    });
  }
}
