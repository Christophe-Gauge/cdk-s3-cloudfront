#!/usr/bin/env python3

import aws_cdk as cdk

from s3_cloudfront.s3_cloudfront_stack import S3CloudfrontStack


app = cdk.App()
S3CloudfrontStack(app, "S3CloudfrontStack",
    env={'region': 'us-east-1'},
    synthesizer=cdk.DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
)

app.synth()
